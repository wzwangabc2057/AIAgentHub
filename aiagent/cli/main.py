#!/usr/bin/env python3
"""
AIAgentHub CLI - Command line interface

Provides interactive and direct command modes:
- aiagent serve     → Start server (API + Scheduler + Worker)
- aiagent worker    → Start worker only (distributed)
- aiagent cli       → Interactive REPL
- aiagent exec      → Direct execution
- aiagent chain     → Chain management
- aiagent attach    → Attach to agent tmux session
"""

import json
import subprocess
import sys
import time

import click
import httpx

from aiagent.config import settings

API_BASE = settings.api_base_url


def _api(method: str, path: str, data: dict = None) -> dict:
    """Make API call to local server"""
    url = f"{API_BASE}{path}"
    try:
        with httpx.Client(timeout=30) as client:
            if method == "GET":
                resp = client.get(url)
            elif method == "POST":
                resp = client.post(url, json=data or {})
            elif method == "PUT":
                resp = client.put(url, json=data or {})
            elif method == "DELETE":
                resp = client.delete(url)
            else:
                raise ValueError(f"Unknown method: {method}")

            if resp.status_code >= 400:
                click.echo(f"Error {resp.status_code}: {resp.text}", err=True)
                return {}
            return resp.json()
    except httpx.ConnectError:
        click.echo("Error: Cannot connect to server. Is 'aiagent serve' running?", err=True)
        return {}


@click.group()
def cli():
    """AIAgentHub - Universal AI Agent Platform"""
    pass


# ===== Server Commands =====

@cli.command()
@click.option("--port", default=None, type=int, help="API port")
def serve(port):
    """Start the main server (API + Scheduler + Worker)"""
    import uvicorn
    p = port or settings.api_port
    click.echo(f"Starting AIAgentHub server on port {p}...")
    uvicorn.run("server:app", host="0.0.0.0", port=p, log_level="info")


@cli.command("worker")
def start_worker():
    """Start worker only (distributed mode)"""
    import asyncio
    from worker import main
    asyncio.run(main())


# ===== Agent Commands =====

@cli.group()
def agents():
    """Agent management"""
    pass


@agents.command("list")
def agents_list():
    """List all agents"""
    data = _api("GET", "/api/agents")
    if not data:
        return
    click.echo(f"{'ID':<25s} {'Name':<20s} {'Status':<10s} {'Node':<20s}")
    click.echo("-" * 75)
    for a in data:
        click.echo(f"{a['_id']:<25s} {a.get('name',''):<20s} {a.get('status',''):<10s} {a.get('node_id',''):<20s}")


@agents.command("create")
@click.argument("agent_id")
@click.argument("name")
@click.option("--description", "-d", default="", help="Agent description")
def agents_create(agent_id, name, description):
    """Create a new agent"""
    data = _api("POST", "/api/agents", {"id": agent_id, "name": name, "description": description})
    if data:
        click.echo(f"Agent created: {agent_id}")


# ===== Execution Commands =====

@cli.command("exec")
@click.argument("agent_id")
@click.option("--prompt", "-p", help="Prompt ID")
@click.option("--inline", "-i", help="Inline prompt text")
@click.option("--var", "-v", multiple=True, help="Variables (key=value)")
@click.option("--timeout", "-t", default=300, type=int)
def execute(agent_id, prompt, inline, var, timeout):
    """Execute an agent with a prompt"""
    variables = {}
    for v in var:
        if "=" in v:
            k, val = v.split("=", 1)
            variables[k] = val

    body = {"variables": variables, "timeout": timeout}
    if prompt:
        body["prompt_id"] = prompt
    elif inline:
        body["inline_prompt"] = inline
    else:
        click.echo("Error: --prompt or --inline required", err=True)
        return

    data = _api("POST", f"/api/execute/{agent_id}", body)
    if data:
        eid = data.get("execution_id", "")
        click.echo(f"Execution {eid} started")
        click.echo(f"Attach: tmux attach -t aah_{agent_id}")


# ===== Chain Commands =====

@cli.group()
def chain():
    """Chain management"""
    pass


@chain.command("list")
@click.option("--status", "-s", default=None)
def chain_list(status):
    """List chains"""
    params = f"?status={status}" if status else ""
    data = _api("GET", f"/api/chains{params}")
    if not data:
        return
    click.echo(f"{'ID':<30s} {'Name':<25s} {'Status':<12s} {'Steps':<6s}")
    click.echo("-" * 73)
    for c in data:
        steps = len(c.get("steps", []))
        click.echo(f"{c['_id']:<30s} {c.get('name',''):<25s} {c.get('status',''):<12s} {steps:<6d}")


@chain.command("status")
@click.argument("chain_id")
def chain_status(chain_id):
    """Show chain status"""
    data = _api("GET", f"/api/chains/{chain_id}")
    if not data:
        return
    click.echo(f"Chain: {data.get('name', '')} ({data['_id']})")
    click.echo(f"Status: {data.get('status', '')}")
    for step in data.get("steps", []):
        status_icon = {"completed": "done", "running": "...", "pending": "-", "failed": "FAIL"}.get(step["status"], step["status"])
        click.echo(f"  Step {step['step']}: {step['agent_id']:<20s} [{status_icon}]")
        if step.get("output_preview"):
            click.echo(f"         Output: {step['output_preview'][:80]}")


@chain.command("cancel")
@click.argument("chain_id")
def chain_cancel(chain_id):
    """Cancel a running chain"""
    data = _api("POST", f"/api/chains/{chain_id}/cancel")
    if data:
        click.echo(f"Chain {chain_id} cancelled")


# ===== Monitor Commands =====

@cli.command()
def status():
    """Show system status"""
    data = _api("GET", "/api/status")
    if not data:
        return
    click.echo(f"Node:       {data.get('node_id', '')}")
    click.echo(f"Agents:     {data.get('agents', {}).get('total', 0)} total, {data.get('agents', {}).get('active', 0)} active")
    click.echo(f"Executions: {data.get('executions', {}).get('running', 0)} running, {data.get('executions', {}).get('completed_today', 0)} completed today")
    click.echo(f"Chains:     {data.get('chains', {}).get('running', 0)} running, {data.get('chains', {}).get('completed_today', 0)} completed today")
    click.echo(f"Schedules:  {data.get('schedules', {}).get('enabled', 0)} enabled / {data.get('schedules', {}).get('total', 0)} total")
    pool = data.get("pool", {})
    click.echo(f"Pool:       {pool.get('active', 0)}/{pool.get('max_concurrent', 0)} active")
    click.echo(f"tmux:       {data.get('tmux_sessions', 0)} sessions")
    workers = data.get("workers", {})
    click.echo(f"Workers:    {workers.get('online', 0)} online / {workers.get('total', 0)} total")


@cli.command()
@click.argument("agent_id")
def watch(agent_id):
    """Watch an agent's execution status (poll every 2s)"""
    click.echo(f"Watching {agent_id}... (Ctrl+C to stop)")
    try:
        while True:
            data = _api("GET", f"/api/executions/running?agent_id={agent_id}")
            if data:
                for ex in data:
                    elapsed = ""
                    click.echo(f"  [{ex['_id']}] status={ex['status']} agent={ex['agent_id']}")
            else:
                click.echo(f"  {agent_id}: idle")
            time.sleep(2)
    except KeyboardInterrupt:
        click.echo("\nStopped watching")


@cli.command()
@click.argument("agent_id")
def attach(agent_id):
    """Attach to an agent's tmux session"""
    session = f"aah_{agent_id}"
    click.echo(f"Attaching to {session}... (Ctrl+B, D to detach)")
    subprocess.run(["tmux", "attach", "-t", session])


# ===== Results =====

@cli.command("results")
@click.argument("target")
def show_results(target):
    """Show results for an agent or chain"""
    # Try as chain first
    if target.startswith("chain_"):
        data = _api("GET", f"/api/results/chain/{target}")
    else:
        data = _api("GET", f"/api/results?agent_id={target}")

    if not data:
        click.echo("No results found")
        return
    for r in data:
        click.echo(f"\n--- {r.get('agent_id', '')} (step {r.get('step', '-')}) ---")
        output = r.get("data", "")
        click.echo(output[:500] + ("..." if len(output) > 500 else ""))


# ===== Workers =====

@cli.group("workers")
def workers_group():
    """Worker/node management"""
    pass


@workers_group.command("list")
def workers_list():
    """List all worker nodes"""
    data = _api("GET", "/api/workers")
    if not data:
        return
    click.echo(f"{'Node':<25s} {'Status':<10s} {'Agents':<8s} {'Heartbeat':<25s}")
    click.echo("-" * 68)
    for w in data:
        agents_count = len(w.get("agents", []))
        hb = str(w.get("last_heartbeat", ""))[:19]
        click.echo(f"{w['_id']:<25s} {w.get('status',''):<10s} {agents_count:<8d} {hb:<25s}")


@workers_group.command("status")
def workers_status():
    """Show cluster status"""
    data = _api("GET", "/api/workers/status")
    if not data:
        return
    nodes = data.get("nodes", {})
    click.echo(f"Nodes:    {nodes.get('online', 0)} online, {nodes.get('offline', 0)} offline")
    click.echo(f"Capacity: {data.get('total_capacity', 0)}")
    click.echo(f"Running:  {data.get('running_tasks', 0)} tasks")


# ===== Schedule Commands =====

@cli.group("schedule")
def schedule_group():
    """Schedule management"""
    pass


@schedule_group.command("list")
def schedule_list():
    """List all schedules"""
    data = _api("GET", "/api/schedules")
    if not data:
        return
    click.echo(f"{'ID':<25s} {'Name':<20s} {'Type':<8s} {'Enabled':<8s} {'Cron/Interval':<20s}")
    click.echo("-" * 81)
    for s in data:
        cron_info = s.get("cron", "") or f"{s.get('interval_seconds', '')}s"
        click.echo(f"{s['_id']:<25s} {s.get('name',''):<20s} {s.get('type',''):<8s} {str(s.get('enabled','')):<8s} {cron_info:<20s}")


@schedule_group.command("enable")
@click.argument("schedule_id")
def schedule_enable(schedule_id):
    """Enable a schedule"""
    _api("POST", f"/api/schedules/{schedule_id}/enable")
    click.echo(f"Schedule {schedule_id} enabled")


@schedule_group.command("disable")
@click.argument("schedule_id")
def schedule_disable(schedule_id):
    """Disable a schedule"""
    _api("POST", f"/api/schedules/{schedule_id}/disable")
    click.echo(f"Schedule {schedule_id} disabled")


@schedule_group.command("trigger")
@click.argument("schedule_id")
def schedule_trigger(schedule_id):
    """Manually trigger a schedule"""
    _api("POST", f"/api/schedules/{schedule_id}/trigger")
    click.echo(f"Schedule {schedule_id} triggered")


# ===== Interactive REPL =====

@cli.command("interactive")
def interactive():
    """Enter interactive CLI mode"""
    click.echo("AIAgentHub CLI v1.0")
    click.echo("Type 'help' for commands, 'quit' to exit.\n")
    while True:
        try:
            cmd = input("aah> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nBye!")
            break

        if not cmd:
            continue
        if cmd in ("quit", "exit"):
            break
        if cmd == "help":
            click.echo("Commands: agents list, exec <agent> --inline <text>, chain list,")
            click.echo("          status, watch <agent>, attach <agent>, results <target>,")
            click.echo("          workers list, schedule list, quit")
            continue

        # Parse and dispatch
        parts = cmd.split()
        try:
            cli.main(parts, standalone_mode=False)
        except SystemExit:
            pass
        except Exception as e:
            click.echo(f"Error: {e}")


def main():
    cli()


if __name__ == "__main__":
    main()
