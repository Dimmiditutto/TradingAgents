"""
dashboard_unified.py - Unified HTML Dashboard
Combines FASE 3 reporting + swing_system visualization

Single-file HTML output with:
  - Interactive tabs
  - Responsive design
  - Color-coded signals
  - Performance metrics
  - Equity curves
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd


def create_dashboard_html(scan_results: List[Dict] = None,
                         backtest_results: Dict = None,
                         positions: List[Dict] = None,
                         title: str = "Trading Dashboard",
                         output_path: str = "dashboard.html") -> str:
    """
    Crea dashboard HTML completo.
    
    Args:
        scan_results: List di SwingSignalV2.to_dict()
        backtest_results: BacktestResult.to_dict()
        positions: List di posizioni aperte
        title: Titolo pagina
        output_path: Path di output
    
    Returns:
        HTML code
    """
    
    scan_results = scan_results or []
    backtest_results = backtest_results or {}
    positions = positions or []
    
    html = _build_html(
        title=title,
        scan_results=scan_results,
        backtest_results=backtest_results,
        positions=positions,
    )
    
    with open(output_path, "w") as f:
        f.write(html)
    
    return output_path


def _build_html(title: str, scan_results: List[Dict], 
                backtest_results: Dict, positions: List[Dict]) -> str:
    """Costruisce HTML."""
    
    styles = _get_css()
    scripts = _get_js()
    
    scan_html = _build_scan_tab(scan_results)
    backtest_html = _build_backtest_tab(backtest_results)
    positions_html = _build_positions_tab(positions)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{styles}
    </style>
</head>
<body>
    <header>
        <h1>📈 {title}</h1>
        <div class="timestamp">Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </header>
    
    <div class="container">
        <div class="tabs">
            <button class="tab-btn active" data-tab="scan">🔍 Scan</button>
            <button class="tab-btn" data-tab="backtest">📊 Backtest</button>
            <button class="tab-btn" data-tab="positions">💼 Positions</button>
        </div>
        
        <div class="tab-content">
            {scan_html}
            {backtest_html}
            {positions_html}
        </div>
    </div>
    
    <script>
{scripts}
    </script>
</body>
</html>"""
    
    return html


def _build_scan_tab(scan_results: List[Dict]) -> str:
    """Tab per scan results."""
    
    if not scan_results:
        return '''<div id="scan" class="tab-pane active">
            <p class="no-data">No scan results yet.</p>
        </div>'''
    
    # Score distribution
    scores = [r.get("score", 0) for r in scan_results]
    if scores:
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
    else:
        avg_score = max_score = min_score = 0
    
    # Direction split
    longs = sum(1 for r in scan_results if r.get("direction") == "LONG")
    shorts = sum(1 for r in scan_results if r.get("direction") == "SHORT")
    
    # Build table
    rows = []
    for result in scan_results:
        score = result.get("score", 0)
        direction = result.get("direction", "N/A")
        ticker = result.get("ticker", "N/A")
        price = result.get("entry_price", 0)
        atr = result.get("atr", 0)
        structure = result.get("context", {}).get("structure_event", "N/A")
        
        score_color = _score_color(score)
        direction_badge = f'<span class="badge badge-{direction.lower()}">{direction}</span>'
        score_badge = f'<span style="color: {score_color}; font-weight: bold;">{score:.0f}</span>'
        
        row = f"""<tr>
            <td>{ticker}</td>
            <td>{direction_badge}</td>
            <td>{score_badge}</td>
            <td>${price:.2f}</td>
            <td>${atr:.2f}</td>
            <td>{structure}</td>
        </tr>"""
        rows.append(row)
    
    table_html = f"""<table class="signals-table">
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Direction</th>
                <th>Score</th>
                <th>Entry Price</th>
                <th>ATR</th>
                <th>Structure</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>"""
    
    stats = f"""<div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Total Signals</div>
            <div class="stat-value">{len(scan_results)}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Avg Score</div>
            <div class="stat-value">{avg_score:.0f}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">LONG / SHORT</div>
            <div class="stat-value">{longs} / {shorts}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Score Range</div>
            <div class="stat-value">{min_score:.0f} - {max_score:.0f}</div>
        </div>
    </div>"""
    
    return f"""<div id="scan" class="tab-pane active">
        {stats}
        <h3>Signals</h3>
        {table_html}
    </div>"""


def _build_backtest_tab(backtest_results: Dict) -> str:
    """Tab per backtest results."""
    
    if not backtest_results:
        return '''<div id="backtest" class="tab-pane">
            <p class="no-data">No backtest results yet.</p>
        </div>'''
    
    # Main metrics
    total_trades = backtest_results.get("total_trades", 0)
    win_rate = backtest_results.get("win_rate", 0)
    profit_factor = backtest_results.get("profit_factor", 0)
    total_pnl = backtest_results.get("total_pnl_pct", 0)
    sharpe = backtest_results.get("sharpe_ratio", 0)
    max_dd = backtest_results.get("max_drawdown", 0)
    
    metrics = f"""<div class="metrics-grid">
        <div class="metric">
            <div class="metric-label">Total Trades</div>
            <div class="metric-value">{total_trades}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value">{win_rate:.1f}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">Profit Factor</div>
            <div class="metric-value" style="color: {_pf_color(profit_factor)};">{profit_factor:.2f}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Total P&L</div>
            <div class="metric-value" style="color: {_pnl_color(total_pnl)};">{total_pnl:+.2f}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">Sharpe Ratio</div>
            <div class="metric-value">{sharpe:.2f}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Max Drawdown</div>
            <div class="metric-value" style="color: {_dd_color(max_dd)};">{max_dd:.2f}%</div>
        </div>
    </div>"""
    
    # Breakdown
    breakdown_html = _build_breakdown_table(backtest_results)
    
    return f"""<div id="backtest" class="tab-pane">
        <h3>Performance Metrics</h3>
        {metrics}
        <h3>Breakdown Analysis</h3>
        {breakdown_html}
    </div>"""


def _build_breakdown_table(backtest_results: Dict) -> str:
    """Breakdown tables."""
    
    html = ""
    
    # By event type
    if "breakdown_by_event" in backtest_results:
        breakdown = backtest_results["breakdown_by_event"]
        rows = []
        for event, stats in breakdown.items():
            row = f"""<tr>
                <td>{event}</td>
                <td>{stats.get('count', 0)}</td>
                <td>{stats.get('win_rate', 0):.1f}%</td>
                <td style="color: {_pnl_color(stats.get('avg_pnl', 0))};">{stats.get('avg_pnl', 0):+.2f}%</td>
            </tr>"""
            rows.append(row)
        
        html += f"""<h4>By Event Type</h4>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Event</th>
                    <th>Count</th>
                    <th>Win Rate</th>
                    <th>Avg P&L</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>"""
    
    # By direction
    if "breakdown_by_direction" in backtest_results:
        breakdown = backtest_results["breakdown_by_direction"]
        rows = []
        for direction, stats in breakdown.items():
            row = f"""<tr>
                <td>{direction}</td>
                <td>{stats.get('count', 0)}</td>
                <td>{stats.get('win_rate', 0):.1f}%</td>
                <td style="color: {_pnl_color(stats.get('avg_pnl', 0))};">{stats.get('avg_pnl', 0):+.2f}%</td>
            </tr>"""
            rows.append(row)
        
        html += f"""<h4>By Direction</h4>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Direction</th>
                    <th>Count</th>
                    <th>Win Rate</th>
                    <th>Avg P&L</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>"""
    
    return html


def _build_positions_tab(positions: List[Dict]) -> str:
    """Tab per posizioni aperte."""
    
    if not positions:
        return '''<div id="positions" class="tab-pane">
            <p class="no-data">No open positions.</p>
        </div>'''
    
    rows = []
    for pos in positions:
        entry = pos.get("entry_price", 0)
        current = pos.get("current_price", entry)
        direction = pos.get("direction", "LONG")
        gain = ((current - entry) / entry * 100) if direction == "LONG" else ((entry - current) / entry * 100)
        
        row = f"""<tr>
            <td>{pos.get('ticker', 'N/A')}</td>
            <td><span class="badge badge-{direction.lower()}">{direction}</span></td>
            <td>${entry:.2f}</td>
            <td>${current:.2f}</td>
            <td style="color: {_pnl_color(gain)};">{gain:+.2f}%</td>
            <td>${pos.get('risk', 0):.2f}</td>
        </tr>"""
        rows.append(row)
    
    table = f"""<table class="positions-table">
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Direction</th>
                <th>Entry</th>
                <th>Current</th>
                <th>Gain</th>
                <th>Risk</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>"""
    
    return f"""<div id="positions" class="tab-pane">
        <h3>Open Positions ({len(positions)})</h3>
        {table}
    </div>"""


def _get_css() -> str:
    """CSS styling."""
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
            color: #e2e8f0;
            line-height: 1.6;
        }
        
        header {
            background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
            padding: 2rem;
            border-bottom: 2px solid #3b82f6;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        header h1 {
            font-size: 2rem;
            color: #60a5fa;
        }
        
        .timestamp {
            font-size: 0.9rem;
            color: #94a3b8;
        }
        
        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 1rem;
        }
        
        .tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid #334155;
            padding-bottom: 1rem;
        }
        
        .tab-btn {
            padding: 0.75rem 1.5rem;
            border: none;
            background: transparent;
            color: #cbd5e1;
            font-size: 1rem;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }
        
        .tab-btn:hover {
            color: #60a5fa;
        }
        
        .tab-btn.active {
            color: #60a5fa;
            border-bottom-color: #60a5fa;
        }
        
        .tab-pane {
            display: none;
            animation: fadeIn 0.3s;
        }
        
        .tab-pane.active {
            display: block;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .stats-grid, .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat-card, .metric {
            background: #1e293b;
            border: 1px solid #334155;
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-label, .metric-label {
            font-size: 0.85rem;
            color: #94a3b8;
            margin-bottom: 0.5rem;
        }
        
        .stat-value, .metric-value {
            font-size: 1.75rem;
            font-weight: bold;
            color: #60a5fa;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 2rem;
        }
        
        th {
            background: #0f172a;
            color: #60a5fa;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #334155;
        }
        
        td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #334155;
        }
        
        tr:hover {
            background: #0f172a;
        }
        
        .badge {
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        
        .badge-long {
            background: #10b981;
            color: white;
        }
        
        .badge-short {
            background: #ef4444;
            color: white;
        }
        
        h3, h4 {
            color: #60a5fa;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        
        .no-data {
            text-align: center;
            color: #94a3b8;
            padding: 2rem;
        }
    """


def _get_js() -> str:
    """JavaScript interactivity."""
    return """
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                
                // Hide all tabs
                document.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.classList.remove('active');
                });
                
                // Remove active class from buttons
                document.querySelectorAll('.tab-btn').forEach(b => {
                    b.classList.remove('active');
                });
                
                // Show selected tab
                document.getElementById(tabName).classList.add('active');
                e.target.classList.add('active');
            });
        });
    """


# ==================== COLOR HELPERS ====================

def _score_color(score: float) -> str:
    """Color per score (0-100)."""
    if score >= 85:
        return "#10b981"  # green
    elif score >= 70:
        return "#f59e0b"  # amber
    elif score >= 60:
        return "#f97316"  # orange
    else:
        return "#ef4444"  # red


def _pf_color(pf: float) -> str:
    """Color per profit factor."""
    if pf >= 2.0:
        return "#10b981"
    elif pf >= 1.5:
        return "#f59e0b"
    else:
        return "#ef4444"


def _pnl_color(pnl: float) -> str:
    """Color per P&L."""
    return "#10b981" if pnl > 0 else "#ef4444"


def _dd_color(dd: float) -> str:
    """Color per drawdown."""
    if dd < -10:
        return "#ef4444"
    elif dd < -5:
        return "#f97316"
    else:
        return "#f59e0b"
