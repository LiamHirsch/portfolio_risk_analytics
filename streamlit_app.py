"""
Portfolio Risk Analytics Dashboard
Professional-grade portfolio management tool for institutional investors

Author: Liam Hirsch
Based on experience at BNP Paribas Luxembourg and Bellecapital AG Zürich
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Portfolio Risk Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 0.3rem solid #1f77b4;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

class PortfolioAnalytics:
    """Core portfolio analytics engine"""
    
    def __init__(self, tickers, weights, start_date, end_date):
        self.tickers = tickers
        self.weights = np.array(weights)
        self.start_date = start_date
        self.end_date = end_date
        self.data = None
        self.returns = None
        
    @st.cache_data
    def fetch_data(_self):
        """Fetch price data for portfolio securities"""
        try:
            data = yf.download(_self.tickers, start=_self.start_date, end=_self.end_date)['Adj Close']
            if len(_self.tickers) == 1:
                data = data.to_frame(name=_self.tickers[0])
            return data.dropna()
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            return None
    
    def calculate_returns(self):
        """Calculate daily returns for each security"""
        if self.data is not None:
            return self.data.pct_change().dropna()
        return None
    
    def portfolio_returns(self):
        """Calculate weighted portfolio returns"""
        if self.returns is not None:
            return (self.returns * self.weights).sum(axis=1)
        return None
    
    def calculate_metrics(self):
        """Calculate comprehensive portfolio metrics"""
        portfolio_rets = self.portfolio_returns()
        
        if portfolio_rets is None or len(portfolio_rets) == 0:
            return {}
        
        # Basic metrics
        total_return = (1 + portfolio_rets).prod() - 1
        annualized_return = portfolio_rets.mean() * 252
        annualized_vol = portfolio_rets.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0
        
        # Risk metrics
        var_95 = np.percentile(portfolio_rets, 5)
        cvar_95 = portfolio_rets[portfolio_rets <= var_95].mean() if len(portfolio_rets[portfolio_rets <= var_95]) > 0 else var_95
        
        # Maximum drawdown
        cumulative = (1 + portfolio_rets).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'Total Return': total_return,
            'Annualized Return': annualized_return,
            'Annualized Volatility': annualized_vol,
            'Sharpe Ratio': sharpe_ratio,
            'VaR (95%)': var_95,
            'CVaR (95%)': cvar_95,
            'Maximum Drawdown': max_drawdown,
            'Portfolio Returns': portfolio_rets,
            'Cumulative Returns': cumulative,
            'Drawdown Series': drawdown
        }
    
    def risk_attribution(self):
        """Calculate risk contribution by asset"""
        if self.returns is None:
            return None
        
        cov_matrix = self.returns.cov() * 252
        portfolio_variance = np.dot(self.weights.T, np.dot(cov_matrix, self.weights))
        
        if portfolio_variance <= 0:
            return None
        
        marginal_contrib = np.dot(cov_matrix, self.weights)
        risk_contrib = self.weights * marginal_contrib / portfolio_variance
        
        return pd.DataFrame({
            'Asset': self.tickers,
            'Weight': self.weights,
            'Risk Contribution': risk_contrib,
            'Risk Contribution %': risk_contrib / risk_contrib.sum() * 100
        })

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">🏦 Portfolio Risk Analytics Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("*Professional-grade portfolio management tool for institutional investors*")
    st.markdown("---")
    
    # Sidebar configuration
    st.sidebar.header("Portfolio Configuration")
    
    # Default portfolio for demo
    default_tickers = "AAPL,MSFT,GOOGL,AMZN,TSLA"
    tickers_input = st.sidebar.text_area(
        "Enter tickers (comma-separated)", 
        value=default_tickers,
        help="Enter stock tickers separated by commas"
    )
    
    # Process tickers
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(',') if ticker.strip()]
    
    if not tickers:
        st.error("Please enter at least one ticker symbol")
        return
    
    # Date range selection
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date", 
            value=datetime.now() - timedelta(days=365),
            max_value=datetime.now()
        )
    with col2:
        end_date = st.date_input(
            "End Date", 
            value=datetime.now(),
            max_value=datetime.now()
        )
    
    # Portfolio weights
    st.sidebar.subheader("Portfolio Weights")
    weights = []
    
    # Equal weights as default
    default_weight = 1.0 / len(tickers)
    
    for ticker in tickers:
        weight = st.sidebar.number_input(
            f"{ticker} Weight", 
            min_value=0.0, 
            max_value=1.0, 
            value=default_weight,
            step=0.01,
            format="%.2f"
        )
        weights.append(weight)
    
    # Normalize weights
    total_weight = sum(weights)
    if total_weight > 0:
        weights = [w / total_weight for w in weights]
    else:
        st.error("Total weights must be greater than 0")
        return
    
    # Display normalized weights
    st.sidebar.write("**Normalized Weights:**")
    for ticker, weight in zip(tickers, weights):
        st.sidebar.write(f"{ticker}: {weight:.1%}")
    
    # Analysis button
    if st.sidebar.button("🔍 Analyze Portfolio", type="primary"):
        
        with st.spinner("Fetching market data and calculating analytics..."):
            
            # Initialize portfolio
            portfolio = PortfolioAnalytics(tickers, weights, start_date, end_date)
            portfolio.data = portfolio.fetch_data()
            
            if portfolio.data is None:
                st.error("Unable to fetch data. Please check your ticker symbols and try again.")
                return
            
            portfolio.returns = portfolio.calculate_returns()
            
            if portfolio.returns is None:
                st.error("Unable to calculate returns.")
                return
            
            # Calculate metrics
            metrics = portfolio.calculate_metrics()
            
            if not metrics:
                st.error("Unable to calculate portfolio metrics.")
                return
            
            # Display results
            st.success("✅ Analysis completed successfully!")
            
            # Portfolio composition
            st.subheader("📊 Portfolio Composition")
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart
                fig_pie = px.pie(
                    values=weights, 
                    names=tickers, 
                    title="Portfolio Weights"
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Weights table
                weights_df = pd.DataFrame({
                    'Ticker': tickers,
                    'Weight': [f"{w:.1%}" for w in weights]
                })
                st.dataframe(weights_df, use_container_width=True, hide_index=True)
            
            # Key metrics
            st.subheader("📈 Key Performance Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Return", 
                    f"{metrics['Total Return']:.2%}",
                    help="Total portfolio return over the period"
                )
                st.metric(
                    "Sharpe Ratio", 
                    f"{metrics['Sharpe Ratio']:.3f}",
                    help="Risk-adjusted return measure"
                )
            
            with col2:
                st.metric(
                    "Annualized Return", 
                    f"{metrics['Annualized Return']:.2%}",
                    help="Annualized portfolio return"
                )
                st.metric(
                    "Max Drawdown", 
                    f"{metrics['Maximum Drawdown']:.2%}",
                    help="Maximum peak-to-trough decline"
                )
            
            with col3:
                st.metric(
                    "Volatility", 
                    f"{metrics['Annualized Volatility']:.2%}",
                    help="Annualized portfolio volatility"
                )
                st.metric(
                    "VaR (95%)", 
                    f"{metrics['VaR (95%)']:.2%}",
                    help="Value at Risk (95% confidence)"
                )
            
            with col4:
                st.metric(
                    "CVaR (95%)", 
                    f"{metrics['CVaR (95%)']:.2%}",
                    help="Conditional Value at Risk"
                )
                
                # Calculate days analyzed
                days_analyzed = len(portfolio.returns)
                st.metric(
                    "Days Analyzed", 
                    f"{days_analyzed}",
                    help="Number of trading days in analysis"
                )
            
            # Performance charts
            st.subheader("📈 Performance Analysis")
            
            tab1, tab2, tab3 = st.tabs(["Cumulative Returns", "Drawdown Analysis", "Returns Distribution"])
            
            with tab1:
                fig_perf = go.Figure()
                fig_perf.add_trace(go.Scatter(
                    x=metrics['Cumulative Returns'].index,
                    y=metrics['Cumulative Returns'].values,
                    mode='lines',
                    name='Portfolio',
                    line=dict(color='#1f77b4', width=2)
                ))
                fig_perf.update_layout(
                    title="Portfolio Cumulative Returns",
                    xaxis_title="Date",
                    yaxis_title="Cumulative Return",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_perf, use_container_width=True)
            
            with tab2:
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(
                    x=metrics['Drawdown Series'].index,
                    y=metrics['Drawdown Series'].values * 100,
                    mode='lines',
                    name='Drawdown',
                    fill='tonexty',
                    line=dict(color='red', width=1)
                ))
                fig_dd.update_layout(
                    title="Portfolio Drawdown",
                    xaxis_title="Date",
                    yaxis_title="Drawdown (%)",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_dd, use_container_width=True)
            
            with tab3:
                fig_hist = px.histogram(
                    x=metrics['Portfolio Returns'] * 100,
                    nbins=50,
                    title="Daily Returns Distribution (%)"
                )
                fig_hist.update_layout(
                    xaxis_title="Daily Return (%)",
                    yaxis_title="Frequency"
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            
            # Risk attribution
            st.subheader("⚠️ Risk Attribution Analysis")
            risk_attr = portfolio.risk_attribution()
            
            if risk_attr is not None:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Risk contribution chart
                    fig_risk = px.bar(
                        risk_attr,
                        x='Asset',
                        y='Risk Contribution %',
                        title="Risk Contribution by Asset"
                    )
                    st.plotly_chart(fig_risk, use_container_width=True)
                
                with col2:
                    # Risk attribution table
                    st.dataframe(
                        risk_attr.style.format({
                            'Weight': '{:.1%}',
                            'Risk Contribution': '{:.4f}',
                            'Risk Contribution %': '{:.1f}%'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **Developed by Liam Hirsch** | Finance & Technology Professional  
    *Based on institutional experience at BNP Paribas Luxembourg and Bellecapital AG Zürich*
    
    📧 [hirschliam17@gmail.com](mailto:hirschliam17@gmail.com) | 
    🔗 [LinkedIn](https://linkedin.com/in/liam-hirsch1709) | 
    💻 [GitHub](https://github.com/LiamHirsch)
    """)

if __name__ == "__main__":
    main()
