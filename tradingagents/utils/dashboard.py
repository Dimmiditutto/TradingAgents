"""
Dashboard con grafici per TradingAgents
Utilizza Plotly per grafici interattivi
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
from typing import Dict, List, Any, Optional
import os


class DashboardGenerator:
    """Generatore di grafici e dashboard trading"""
    
    def __init__(self, output_dir: str = "./dashboards"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def create_decision_gauge(
        self,
        decision_score: float,
        sentiment: str = "neutro"
    ) -> go.Figure:
        """
        Crea gauge chart per la decisione trading
        
        Args:
            decision_score: Score da -1 (vendita) a 1 (acquisto)
            sentiment: 'rialzista', 'ribassista' o 'neutro'
            
        Returns:
            Plotly figure
        """
        
        # Determina colore base su sentiment
        color_map = {
            'rialzista': '#2ecc71',
            'neutro': '#f39c12',
            'ribassista': '#e74c3c'
        }
        
        color = color_map.get(sentiment, '#95a5a6')
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=decision_score * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "DECISIONE TRADING"},
            delta={'reference': 0},
            gauge={
                'axis': {'range': [-100, 100]},
                'bar': {'color': color},
                'steps': [
                    {'range': [-100, -33], 'color': '#fadbd8'},
                    {'range': [-33, 33], 'color': '#ffeaa7'},
                    {'range': [33, 100], 'color': '#d5f4e6'}
                ],
                'threshold': {
                    'line': {'color': 'red', 'width': 4},
                    'thickness': 0.75,
                    'value': 0
                }
            }
        ))
        
        fig.update_layout(
            font={'size': 12},
            height=400,
            margin=dict(l=20, r=20, t=70, b=20)
        )
        
        return fig
    
    def create_sentiment_breakdown(
        self,
        sentiments: Dict[str, float]
    ) -> go.Figure:
        """
        Crea pie chart con breakdown dei sentiment
        
        Args:
            sentiments: {nome_analista: score}
            
        Returns:
            Plotly figure
        """
        
        sentiments_list = list(sentiments.keys())
        values = [abs(v) for v in sentiments.values()]
        
        # Colori basati sul valore
        colors = []
        for v in sentiments.values():
            if v > 0:
                colors.append('#2ecc71')  # verde - rialzista
            elif v < 0:
                colors.append('#e74c3c')  # rosso - ribassista
            else:
                colors.append('#95a5a6')  # grigio - neutro
        
        fig = go.Figure(data=[go.Pie(
            labels=sentiments_list,
            values=values,
            marker=dict(colors=colors),
            textposition='inside',
            textinfo='label+percent'
        )])
        
        fig.update_layout(
            title="CONSENSUS ANALISTI",
            font={'size': 11},
            height=400,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        
        return fig
    
    def create_price_chart(
        self,
        ticker: str,
        dates: List[str],
        prices: List[float],
        moving_avg_20: Optional[List[float]] = None,
        moving_avg_50: Optional[List[float]] = None
    ) -> go.Figure:
        """
        Crea grafico dei prezzi con medie mobili
        
        Args:
            ticker: Simbolo titolo
            dates: Lista di date
            prices: Lista di prezzi
            moving_avg_20: Media mobile 20 giorni
            moving_avg_50: Media mobile 50 giorni
            
        Returns:
            Plotly figure
        """
        
        fig = go.Figure()
        
        # Prezzo
        fig.add_trace(go.Scatter(
            x=dates,
            y=prices,
            mode='lines',
            name='Prezzo',
            line=dict(color='#3498db', width=2)
        ))
        
        # Media mobile 20
        if moving_avg_20:
            fig.add_trace(go.Scatter(
                x=dates,
                y=moving_avg_20,
                mode='lines',
                name='MA 20',
                line=dict(color='#f39c12', width=1, dash='dash')
            ))
        
        # Media mobile 50
        if moving_avg_50:
            fig.add_trace(go.Scatter(
                x=dates,
                y=moving_avg_50,
                mode='lines',
                name='MA 50',
                line=dict(color='#e74c3c', width=1, dash='dash')
            ))
        
        fig.update_layout(
            title=f"ANDAMENTO PREZZO {ticker}",
            xaxis_title="Data",
            yaxis_title="Prezzo (€)",
            height=400,
            hovermode='x unified',
            font={'size': 10},
            margin=dict(l=50, r=20, t=50, b=50)
        )
        
        fig.update_xaxes(rangeslider_visible=False)
        
        return fig
    
    def create_analyst_comparison(
        self,
        analysts: Dict[str, Dict[str, Any]]
    ) -> go.Figure:
        """
        Crea radar chart per confronto analisti
        
        Args:
            analysts: {
                'nome': {
                    'sentiment': float,
                    'confidence': float,
                    'accuracy': float
                }
            }
            
        Returns:
            Plotly figure
        """
        
        categories = ['Sentiment', 'Confidence', 'Accuratezza']
        
        fig = go.Figure()
        
        for analyst_name, metrics in analysts.items():
            values = [
                metrics.get('sentiment', 0),
                metrics.get('confidence', 0),
                metrics.get('accuracy', 0)
            ]
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=analyst_name
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[-1, 1]
                )
            ),
            title="CONFRONTO ANALISTI",
            height=400,
            font={'size': 10},
            margin=dict(l=80, r=80, t=50, b=20)
        )
        
        return fig
    
    def create_performance_table(
        self,
        performance_data: List[Dict[str, Any]]
    ) -> go.Figure:
        """
        Crea tabella con dati di performance
        
        Args:
            performance_data: Lista di dizionari con dati
            
        Returns:
            Plotly figure
        """
        
        if not performance_data:
            return go.Figure()
        
        columns = list(performance_data[0].keys())
        
        header_values = [f"<b>{col}</b>" for col in columns]
        cell_values = [[str(row.get(col, '')) for col in columns] for row in performance_data]
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=header_values,
                fill_color='#3498db',
                align='center',
                font=dict(color='white', size=12)
            ),
            cells=dict(
                values=cell_values,
                fill_color='#ecf0f1',
                align='center',
                font=dict(size=11),
                height=30
            )
        )])
        
        fig.update_layout(
            title="DATI PERFORMANCE",
            height=400,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        
        return fig
    
    def create_dashboard_html(
        self,
        ticker: str,
        decision_fig: go.Figure,
        sentiment_fig: go.Figure,
        price_fig: Optional[go.Figure] = None,
        analyst_fig: Optional[go.Figure] = None,
        performance_fig: Optional[go.Figure] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Crea dashboard HTML completo
        
        Args:
            ticker: Simbolo titolo
            decision_fig: Gauge chart decisione
            sentiment_fig: Pie chart sentiment
            price_fig: Grafico prezzi
            analyst_fig: Radar chart analisti
            performance_fig: Tabella performance
            filename: Nome file HTML
            
        Returns:
            Percorso del file HTML
        """
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dashboard_{ticker}_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Crea HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="it">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Dashboard Trading - {ticker}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                }}
                
                header {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                
                header h1 {{
                    color: #2c3e50;
                    margin-bottom: 10px;
                    font-size: 2.5em;
                }}
                
                header p {{
                    color: #7f8c8d;
                    font-size: 1.1em;
                }}
                
                .info-bar {{
                    display: flex;
                    justify-content: space-around;
                    margin-top: 20px;
                    border-top: 1px solid #ecf0f1;
                    padding-top: 20px;
                }}
                
                .info-item {{
                    text-align: center;
                }}
                
                .info-label {{
                    font-size: 0.9em;
                    color: #95a5a6;
                    text-transform: uppercase;
                    margin-bottom: 5px;
                }}
                
                .info-value {{
                    font-size: 1.3em;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                
                .card {{
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    transition: transform 0.3s ease;
                }}
                
                .card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
                }}
                
                .card h2 {{
                    color: #2c3e50;
                    margin-bottom: 15px;
                    font-size: 1.3em;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 10px;
                }}
                
                .full-width {{
                    grid-column: 1 / -1;
                }}
                
                footer {{
                    text-align: center;
                    color: white;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid rgba(255, 255, 255, 0.2);
                }}
                
                .timestamp {{
                    font-size: 0.9em;
                    color: #95a5a6;
                }}
                
                @media (max-width: 768px) {{
                    .grid {{
                        grid-template-columns: 1fr;
                    }}
                    
                    header h1 {{
                        font-size: 1.8em;
                    }}
                    
                    .info-bar {{
                        flex-direction: column;
                        gap: 15px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>📊 Dashboard Trading</h1>
                    <p>Analisi Completa di {ticker}</p>
                    <div class="info-bar">
                        <div class="info-item">
                            <div class="info-label">Data Analisi</div>
                            <div class="info-value">{datetime.now().strftime("%d/%m/%Y")}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Titolo</div>
                            <div class="info-value">{ticker}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Ora Analisi</div>
                            <div class="info-value">{datetime.now().strftime("%H:%M:%S")}</div>
                        </div>
                    </div>
                </header>
                
                <div class="grid">
                    <div class="card">
                        <h2>🎯 Decisione Trading</h2>
                        <div id="decision-chart"></div>
                    </div>
                    
                    <div class="card">
                        <h2>📈 Consensus Analisti</h2>
                        <div id="sentiment-chart"></div>
                    </div>
        """
        
        if price_fig:
            html_content += """
                    <div class="card full-width">
                        <h2>💹 Andamento Prezzo</h2>
                        <div id="price-chart"></div>
                    </div>
            """
        
        if analyst_fig:
            html_content += """
                    <div class="card">
                        <h2>👥 Confronto Analisti</h2>
                        <div id="analyst-chart"></div>
                    </div>
            """
        
        if performance_fig:
            html_content += """
                    <div class="card full-width">
                        <h2>📊 Dati Performance</h2>
                        <div id="performance-chart"></div>
                    </div>
            """
        
        html_content += """
                </div>
                
                <footer>
                    <p>Generato da TradingAgents - Sistema di Analisi Trading Automatico</p>
                    <p class="timestamp">""" + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + """</p>
                </footer>
            </div>
            
            <script>
        """
        
        # Aggiungi grafici Plotly
        html_content += f"Plotly.newPlot('decision-chart', {decision_fig.to_json()}, {{}}, {{responsive: true}});\n"
        html_content += f"Plotly.newPlot('sentiment-chart', {sentiment_fig.to_json()}, {{}}, {{responsive: true}});\n"
        
        if price_fig:
            html_content += f"Plotly.newPlot('price-chart', {price_fig.to_json()}, {{}}, {{responsive: true}});\n"
        
        if analyst_fig:
            html_content += f"Plotly.newPlot('analyst-chart', {analyst_fig.to_json()}, {{}}, {{responsive: true}});\n"
        
        if performance_fig:
            html_content += f"Plotly.newPlot('performance-chart', {performance_fig.to_json()}, {{}}, {{responsive: true}});\n"
        
        html_content += """
            </script>
        </body>
        </html>
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
