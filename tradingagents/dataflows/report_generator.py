"""
Report Generator - Create HTML/PDF Reports with Charts

Architecture:
  1. HTML Report Generation (styled, responsive)
  2. Plotly Charts (price action + indicators)
  3. Ranked Signal Tables
  4. Export to file (HTML/PDF)
  5. Email delivery capability

Purpose: Professional screener reports for daily/weekly review
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from typing import List, Dict, Optional
import base64
from io import BytesIO

from .multi_timeframe import MultiTimeframeLayer, MultiTimeframeData
from .scoring_engine import ScoringEngine, SignalScore, TradeDirection
from .structure_detector import SwingClassifier
from .backtester import BacktestResult


class ReportGenerator:
    """Generate professional HTML reports with charts"""
    
    def __init__(self):
        self.mtf_layer = MultiTimeframeLayer()
        self.scorer = ScoringEngine()
        self.classifier = SwingClassifier()
    
    def generate_screener_report(
        self,
        symbols: List[str],
        output_path: str = None,
        title: str = "Swing Trading Screener Report",
        min_score: float = 50.0
    ) -> str:
        """
        Generate comprehensive screener report
        
        Args:
            symbols: List of ticker symbols to analyze
            output_path: File path for HTML output (None = return HTML string)
            title: Report title
            min_score: Minimum score threshold for inclusion
        
        Returns:
            HTML string (also saves to file if output_path provided)
        """
        
        print(f"\n📊 Generating screener report for {len(symbols)} symbols...")
        
        # Collect all signals
        all_signals = []
        
        for symbol in symbols:
            try:
                print(f"  Analyzing {symbol}...", end=" ", flush=True)
                
                mtf = self.mtf_layer.fetch_symbol_mtf(symbol)
                long_score, short_score = self.scorer.score_mtf_signal(mtf)
                
                all_signals.append({
                    'symbol': symbol,
                    'long_score': long_score,
                    'short_score': short_score,
                    'mtf': mtf,
                })
                
                print(f"✓ L:{long_score.total_score:.0f} S:{short_score.total_score:.0f}")
                
            except Exception as e:
                print(f"⚠️ Error: {e}")
                continue
        
        # Filter by min score
        high_quality = []
        for sig in all_signals:
            if sig['long_score'].total_score >= min_score or \
               sig['short_score'].total_score >= min_score:
                high_quality.append(sig)
        
        print(f"\n✅ Analysis complete: {len(high_quality)}/{len(all_signals)} symbols above {min_score:.0f} threshold")
        
        # Generate HTML
        html = self._build_html_report(
            signals=high_quality,
            title=title,
            timestamp=datetime.now()
        )
        
        # Save to file
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"\n💾 Report saved to: {output_path}")
        
        return html
    
    def _build_html_report(
        self,
        signals: List[Dict],
        title: str,
        timestamp: datetime
    ) -> str:
        """Build complete HTML report"""
        
        # Sort signals by best score (LONG or SHORT)
        signals_sorted = sorted(
            signals,
            key=lambda s: max(s['long_score'].total_score, s['short_score'].total_score),
            reverse=True
        )
        
        # HTML header with CSS
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header .timestamp {{
            font-size: 1em;
            opacity: 0.9;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }}
        
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .summary-card .label {{
            font-size: 0.9em;
            color: #6c757d;
        }}
        
        .signals-section {{
            padding: 40px;
        }}
        
        .signal-card {{
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .signal-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }}
        
        .signal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e9ecef;
        }}
        
        .signal-symbol {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .signal-scores {{
            display: flex;
            gap: 20px;
        }}
        
        .score-badge {{
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .score-long {{
            background: #d4edda;
            color: #155724;
            border: 2px solid #28a745;
        }}
        
        .score-short {{
            background: #f8d7da;
            color: #721c24;
            border: 2px solid #dc3545;
        }}
        
        .score-high {{
            background: #28a745;
            color: white;
        }}
        
        .score-moderate {{
            background: #ffc107;
            color: #333;
        }}
        
        .score-low {{
            background: #6c757d;
            color: white;
        }}
        
        .signal-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .detail-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .detail-box h4 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1em;
        }}
        
        .detail-box ul {{
            list-style: none;
            font-size: 0.9em;
            line-height: 1.8;
        }}
        
        .detail-box ul li {{
            padding: 3px 0;
        }}
        
        .strength {{
            color: #28a745;
        }}
        
        .weakness {{
            color: #dc3545;
        }}
        
        .chart-container {{
            margin-top: 20px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
        
        @media print {{
            body {{
                padding: 0;
                background: white;
            }}
            
            .signal-card {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {title}</h1>
            <div class="timestamp">Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="value">{len(signals)}</div>
                <div class="label">Signals Analyzed</div>
            </div>
            <div class="summary-card">
                <div class="value">{len([s for s in signals if s['long_score'].total_score >= 75])}</div>
                <div class="label">Strong LONG Setups</div>
            </div>
            <div class="summary-card">
                <div class="value">{len([s for s in signals if s['short_score'].total_score >= 75])}</div>
                <div class="label">Strong SHORT Setups</div>
            </div>
            <div class="summary-card">
                <div class="value">{round(sum(max(s['long_score'].total_score, s['short_score'].total_score) for s in signals) / len(signals) if signals else 0, 1)}</div>
                <div class="label">Average Score</div>
            </div>
        </div>
        
        <div class="signals-section">
            <h2 style="margin-bottom: 30px; color: #2c3e50;">🎯 Top Signals</h2>
"""
        
        # Add each signal card
        for sig in signals_sorted:
            html += self._build_signal_card(sig)
        
        # Footer
        html += """
        </div>
        
        <div class="footer">
            <p>TradingAgents Multi-Timeframe Analysis System | FASE 3</p>
            <p>⚠️ Not financial advice. For educational purposes only.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def _build_signal_card(self, signal: Dict) -> str:
        """Build HTML card for single signal"""
        
        symbol = signal['symbol']
        long_score = signal['long_score']
        short_score = signal['short_score']
        mtf = signal['mtf']
        
        # Determine primary direction
        if long_score.total_score > short_score.total_score:
            primary_direction = "LONG"
            primary_score = long_score
            score_class = "score-long"
        else:
            primary_direction = "SHORT"
            primary_score = short_score
            score_class = "score-short"
        
        # Score category
        if primary_score.total_score >= 75:
            category = "STRONG"
            category_class = "score-high"
        elif primary_score.total_score >= 50:
            category = "MODERATE"
            category_class = "score-moderate"
        else:
            category = "WEAK"
            category_class = "score-low"
        
        # Build card HTML
        html = f"""
            <div class="signal-card">
                <div class="signal-header">
                    <div class="signal-symbol">{symbol}</div>
                    <div class="signal-scores">
                        <div class="score-badge {score_class}">{primary_direction}: {primary_score.total_score:.0f}/100</div>
                        <div class="score-badge {category_class}">{category}</div>
                    </div>
                </div>
                
                <div class="signal-details">
                    <div class="detail-box">
                        <h4>📈 Score Breakdown</h4>
                        <ul>
                            <li>Trend: {primary_score.trend_strength:.0f}/100</li>
                            <li>Confluence: {primary_score.direction_confluence:.0f}/100</li>
                            <li>Volume: {primary_score.volume_quality:.0f}/100</li>
                            <li>Structure: {primary_score.structure_quality:.0f}/100</li>
                            <li>Risk: {primary_score.risk_profile:.0f}/100</li>
                        </ul>
                    </div>
                    
                    <div class="detail-box">
                        <h4>📊 Key Metrics</h4>
                        <ul>
                            <li>ADX: {primary_score.adx_value:.1f}</li>
                            <li>Volume Ratio: {primary_score.volume_ratio:.2f}</li>
                            <li>ATR%: {primary_score.atr_pct:.2f}%</li>
                            <li>% from 200 SMA: {primary_score.pct_from_200sma:.1f}%</li>
                            <li>Weekly Trend: {'UP' if primary_score.weekly_trend > 0 else 'DOWN' if primary_score.weekly_trend < 0 else 'FLAT'}</li>
                        </ul>
                    </div>
                    
                    <div class="detail-box">
                        <h4>✅ Strengths</h4>
                        <ul>
"""
        
        for strength in primary_score.strengths[:3]:
            html += f"                            <li class=\"strength\">✓ {strength}</li>\n"
        
        html += """
                        </ul>
                    </div>
                    
                    <div class="detail-box">
                        <h4>⚠️ Weaknesses</h4>
                        <ul>
"""
        
        if primary_score.weaknesses:
            for weakness in primary_score.weaknesses[:3]:
                html += f"                            <li class=\"weakness\">⚠ {weakness}</li>\n"
        else:
            html += "                            <li>None significant</li>\n"
        
        html += """
                        </ul>
                    </div>
                </div>
                
                <div class="chart-container">
"""
        
        # Add chart
        chart_div = self._create_chart(mtf, symbol)
        html += chart_div
        
        html += """
                </div>
            </div>
"""
        
        return html
    
    def _create_chart(self, mtf: MultiTimeframeData, symbol: str) -> str:
        """Create Plotly chart for symbol"""
        
        df = mtf.daily.ohlcv.tail(60)  # Last 60 days
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(f'{symbol} Price Action', 'Volume', 'ADX')
        )
        
        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df['date'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                increasing_line_color='#28a745',
                decreasing_line_color='#dc3545'
            ),
            row=1, col=1
        )
        
        # 200 SMA
        sma_200 = mtf.daily.indicators.get('close_200_sma')
        if sma_200 is not None and len(sma_200) > 0:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=sma_200.tail(60),
                    mode='lines',
                    name='200 SMA',
                    line=dict(color='blue', width=2)
                ),
                row=1, col=1
            )
        
        # SuperTrend
        supertrend = mtf.daily.indicators.get('supertrend')
        if supertrend is not None and len(supertrend) > 0:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=supertrend.tail(60),
                    mode='lines',
                    name='SuperTrend',
                    line=dict(color='purple', width=2, dash='dash')
                ),
                row=1, col=1
            )
        
        # Volume bars
        colors = ['#28a745' if df.iloc[i]['close'] >= df.iloc[i]['open'] else '#dc3545' 
                  for i in range(len(df))]
        
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['volume'],
                name='Volume',
                marker_color=colors,
                showlegend=False
            ),
            row=2, col=1
        )
        
        # ADX
        adx = mtf.daily.indicators.get('adx')
        if adx is not None and len(adx) > 0:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=adx.tail(60),
                    mode='lines',
                    name='ADX',
                    line=dict(color='orange', width=2),
                    showlegend=False
                ),
                row=3, col=1
            )
            
            # ADX threshold line at 25
            fig.add_hline(
                y=25,
                line_dash="dash",
                line_color="gray",
                row=3, col=1
            )
        
        # Update layout
        fig.update_layout(
            height=800,
            showlegend=True,
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=10)
        )
        
        # Update y-axes
        fig.update_yaxes(title_text="Price", row=1, col=1, gridcolor='#e9ecef')
        fig.update_yaxes(title_text="Volume", row=2, col=1, gridcolor='#e9ecef')
        fig.update_yaxes(title_text="ADX", row=3, col=1, gridcolor='#e9ecef')
        
        # Convert to HTML div
        chart_html = fig.to_html(include_plotlyjs=False, div_id=f"chart_{symbol}")
        
        return chart_html
    
    def generate_backtest_report(
        self,
        result: BacktestResult,
        output_path: str = None
    ) -> str:
        """Generate HTML report for backtest results"""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Backtest Report - {result.symbol}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        
        .header {{
            background: #2c3e50;
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        
        .metric-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        
        table {{
            width: 100%;
            background: white;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        th {{
            background: #34495e;
            color: white;
        }}
        
        .positive {{
            color: #27ae60;
            font-weight: bold;
        }}
        
        .negative {{
            color: #e74c3c;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📈 Backtest Report: {result.symbol}</h1>
        <p>{result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}</p>
    </div>
    
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value">{result.total_trades}</div>
            <div class="metric-label">Total Trades</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{result.win_rate:.1f}%</div>
            <div class="metric-label">Win Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{result.profit_factor:.2f}</div>
            <div class="metric-label">Profit Factor</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${result.total_pnl:.2f}</div>
            <div class="metric-label">Total P&L</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{result.sharpe_ratio:.2f}</div>
            <div class="metric-label">Sharpe Ratio</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{result.max_drawdown:.1f}%</div>
            <div class="metric-label">Max Drawdown</div>
        </div>
    </div>
    
    <h2>Trade Log</h2>
    <table>
        <thead>
            <tr>
                <th>Direction</th>
                <th>Entry Date</th>
                <th>Entry Price</th>
                <th>Exit Date</th>
                <th>Exit Price</th>
                <th>Exit Reason</th>
                <th>P&L</th>
                <th>P&L %</th>
                <th>Bars</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for trade in result.trades:
            pnl_class = "positive" if trade.pnl > 0 else "negative"
            html += f"""
            <tr>
                <td>{trade.direction}</td>
                <td>{trade.entry_date.strftime('%Y-%m-%d')}</td>
                <td>${trade.entry_price:.2f}</td>
                <td>{trade.exit_date.strftime('%Y-%m-%d') if trade.exit_date else '-'}</td>
                <td>${trade.exit_price:.2f if trade.exit_price else 0}</td>
                <td>{trade.exit_reason or '-'}</td>
                <td class="{pnl_class}">${trade.pnl:.2f}</td>
                <td class="{pnl_class}">{trade.pnl_pct:.2f}%</td>
                <td>{trade.bars_held}</td>
            </tr>
"""
        
        html += """
        </tbody>
    </table>
</body>
</html>
"""
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"\n💾 Backtest report saved to: {output_path}")
        
        return html


# ==================== EXAMPLE USAGE ====================

def example_generate_report():
    """Example: Generate screener report"""
    
    generator = ReportGenerator()
    
    symbols = ["SPY", "QQQ", "AAPL", "MSFT"]
    
    html = generator.generate_screener_report(
        symbols=symbols,
        output_path="screener_report.html",
        title="Daily Swing Trading Screener",
        min_score=50.0
    )
    
    print(f"\n✅ Report generated successfully!")
    print(f"   Open screener_report.html in your browser")


if __name__ == "__main__":
    example_generate_report()
