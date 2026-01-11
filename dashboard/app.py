#!/usr/bin/env python3
"""
Trading Engine Metrics Dashboard

A separate Streamlit application for visualizing and mapping metrics over time.
Queries from QuestDB or falls back to Parquet exports.

Run: streamlit run dashboard/app.py
Opens: http://localhost:8501
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Trading Engine Metrics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title('📊 Trading Engine Metrics Dashboard')

# Sidebar configuration
st.sidebar.header('Configuration')
data_source = st.sidebar.radio(
    'Data Source',
    ['QuestDB', 'Parquet Export'],
    index=0,
    help='Select data source: QuestDB (live) or Parquet (exported)'
)

questdb_host = st.sidebar.text_input(
    'QuestDB Host',
    value='localhost',
    help='QuestDB server hostname'
)

questdb_port = st.sidebar.number_input(
    'QuestDB Port',
    value=8812,
    min_value=1,
    max_value=65535,
    help='QuestDB PostgreSQL wire protocol port (default: 8812)'
)


@st.cache_data(ttl=60)
def load_data_from_questdb(host: str = 'localhost', port: int = 8812):
    """
    Load trading metrics from QuestDB using PostgreSQL wire protocol.
    
    Args:
        host: QuestDB hostname
        port: QuestDB PostgreSQL port (default 8812)
        
    Returns:
        DataFrame with trading metrics
    """
    try:
        import psycopg2
        import os
        
        # Use environment variables for credentials, fallback to defaults
        db_user = os.getenv('QUESTDB_USER', 'admin')
        db_password = os.getenv('QUESTDB_PASSWORD', 'quest')
        db_name = os.getenv('QUESTDB_DATABASE', 'qdb')
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        query = """
            SELECT 
                timestamp,
                symbol,
                strategy,
                deployed_capital_pct,
                available_capital,
                deployed_capital,
                total_capital,
                realized_pnl,
                unrealized_pnl,
                open_positions,
                current_price
            FROM trading_metrics
            ORDER BY timestamp DESC
            LIMIT 10000
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
        
    except Exception as e:
        st.error(f"Failed to connect to QuestDB: {e}")
        st.info("Make sure QuestDB is running: `docker run -d -p 9000:9000 -p 8812:8812 -p 9009:9009 questdb/questdb`")
        return None


@st.cache_data
def load_data_from_parquet(filepath: str = 'exports/metrics.parquet'):
    """
    Load trading metrics from Parquet file.
    
    Args:
        filepath: Path to Parquet file
        
    Returns:
        DataFrame with trading metrics
    """
    try:
        parquet_path = Path(filepath)
        if not parquet_path.exists():
            st.error(f"Parquet file not found: {filepath}")
            st.info("Export metrics from the engine or use the 'Export to Parquet' button below.")
            return None
        
        df = pd.read_parquet(filepath)
        
        # Convert timestamp to datetime if needed
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
        
    except Exception as e:
        st.error(f"Failed to load Parquet file: {e}")
        return None


# Load data based on selected source
if data_source == 'QuestDB':
    df = load_data_from_questdb(questdb_host, questdb_port)
else:
    df = load_data_from_parquet()

# Main dashboard
if df is not None and not df.empty:
    st.success(f"✅ Loaded {len(df)} records from {data_source}")
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        latest_pnl = df['realized_pnl'].iloc[0] if 'realized_pnl' in df.columns and len(df) > 0 else 0
        st.metric("Latest Realized PnL", f"${latest_pnl:,.2f}")
    
    with col2:
        latest_deployed = df['deployed_capital_pct'].iloc[0] if 'deployed_capital_pct' in df.columns and len(df) > 0 else 0
        st.metric("Deployed Capital %", f"{latest_deployed:.2f}%")
    
    with col3:
        total_capital = df['total_capital'].iloc[0] if 'total_capital' in df.columns and len(df) > 0 else 0
        st.metric("Total Capital", f"${total_capital:,.2f}")
    
    with col4:
        open_positions_raw = df['open_positions'].iloc[0] if 'open_positions' in df.columns and len(df) > 0 else 0
        # Safe conversion to int, handling NaN and non-numeric values
        try:
            import pandas as pd
            if pd.notna(open_positions_raw):
                open_positions = int(float(open_positions_raw))
            else:
                open_positions = 0
        except (ValueError, TypeError):
            open_positions = 0
        st.metric("Open Positions", open_positions)
    
    # Tabs for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Time Series",
        "🔥 Heatmaps",
        "📊 Statistics",
        "📋 Raw Data"
    ])
    
    with tab1:
        st.subheader("PnL and Deployed Capital Over Time")
        
        # Filter by strategy
        if 'strategy' in df.columns:
            strategies = df['strategy'].unique().tolist()
            selected_strategies = st.multiselect(
                'Filter by Strategy',
                strategies,
                default=strategies,
                key='time_series_strategy'
            )
            df_filtered = df[df['strategy'].isin(selected_strategies)]
        else:
            df_filtered = df
        
        # Create dual-axis plot
        fig = go.Figure()
        
        # Verify required columns exist
        has_pnl = 'realized_pnl' in df_filtered.columns
        has_deployed = 'deployed_capital_pct' in df_filtered.columns
        
        if not has_pnl and not has_deployed:
            st.warning("Required columns 'realized_pnl' or 'deployed_capital_pct' not found in data")
        elif df_filtered.empty:
            st.warning("No data available after filtering")
        else:
            # Group by strategy for color coding
            if 'strategy' in df_filtered.columns:
                strategies = df_filtered['strategy'].unique()
                if len(strategies) == 0:
                    st.warning("No strategies found in filtered data")
                else:
                    for strategy in strategies:
                        df_strategy = df_filtered[df_filtered['strategy'] == strategy]
                        
                        if df_strategy.empty:
                            continue
                        
                        # Realized PnL line
                        if has_pnl:
                            fig.add_trace(go.Scatter(
                                x=df_strategy['timestamp'],
                                y=df_strategy['realized_pnl'],
                                name=f'{strategy} - Realized PnL',
                                mode='lines+markers',
                                yaxis='y1'
                            ))
                        
                        # Deployed Capital % line
                        if has_deployed:
                            fig.add_trace(go.Scatter(
                                x=df_strategy['timestamp'],
                                y=df_strategy['deployed_capital_pct'],
                                name=f'{strategy} - Deployed %',
                                mode='lines+markers',
                                yaxis='y2',
                                line=dict(dash='dash')
                            ))
        
        fig.update_layout(
            hovermode='x unified',
            xaxis=dict(title='Timestamp'),
            yaxis=dict(title='Realized PnL ($)', side='left'),
            yaxis2=dict(title='Deployed Capital (%)', side='right', overlaying='y'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Additional metrics over time
        st.subheader("Additional Metrics")
        
        metric_options = [col for col in df_filtered.columns if col not in ['timestamp', 'symbol', 'strategy']]
        selected_metrics = st.multiselect(
            'Select Metrics to Display',
            metric_options,
            default=['unrealized_pnl', 'current_price'][:min(2, len(metric_options))],
            key='additional_metrics'
        )
        
        if selected_metrics:
            fig_additional = px.line(
                df_filtered,
                x='timestamp',
                y=selected_metrics,
                color='strategy' if 'strategy' in df_filtered.columns else None,
                title='Selected Metrics Over Time'
            )
            fig_additional.update_layout(hovermode='x unified', height=400)
            st.plotly_chart(fig_additional, use_container_width=True)
    
    with tab2:
        st.subheader("Metric Correlations Heatmap")
        
        # Select numeric columns for correlation
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        
        # Remove timestamp if it's numeric
        numeric_cols = [col for col in numeric_cols if col not in ['timestamp', 'open_positions']]
        
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr()
            
            fig_heat = px.imshow(
                corr,
                text_auto='.2f',
                title='Metric Correlations',
                color_continuous_scale='RdBu_r',
                aspect='auto'
            )
            fig_heat.update_layout(height=600)
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.warning("Not enough numeric columns for correlation analysis")
        
        # Deployed Capital % Heatmap over time
        if 'timestamp' in df.columns and 'deployed_capital_pct' in df.columns:
            st.subheader("Deployed Capital % Heat Map Over Time")
            
            # Create time-based bins
            df_heatmap = df.copy()
            
            # Drop rows with NaN timestamps
            df_heatmap = df_heatmap.dropna(subset=['timestamp'])
            
            if df_heatmap.empty:
                st.warning("No valid timestamp data available for heatmap")
            else:
                df_heatmap['hour'] = df_heatmap['timestamp'].dt.hour
                df_heatmap['date'] = df_heatmap['timestamp'].dt.date
                
                try:
                    pivot_data = df_heatmap.pivot_table(
                        values='deployed_capital_pct',
                        index='hour',
                        columns='date',
                        aggfunc='mean'
                    )
                    
                    if not pivot_data.empty:
                        fig_time_heat = px.imshow(
                            pivot_data,
                            title='Deployed Capital % by Hour and Date',
                            labels=dict(x="Date", y="Hour of Day", color="Deployed %"),
                            color_continuous_scale='YlOrRd',
                            aspect='auto'
                        )
                        fig_time_heat.update_layout(height=500)
                        st.plotly_chart(fig_time_heat, use_container_width=True)
                    else:
                        st.warning("No data available for time-based heatmap")
                except Exception as e:
                    st.error(f"Failed to create heatmap: {str(e)}")
    
    with tab3:
        st.subheader("Statistical Summary")
        
        # Strategy-wise statistics
        if 'strategy' in df.columns:
            st.write("**Performance by Strategy**")
            
            # Build aggregation dict based on available columns
            agg_dict = {}
            if 'realized_pnl' in df.columns:
                agg_dict['realized_pnl'] = ['mean', 'std', 'min', 'max']
            if 'deployed_capital_pct' in df.columns:
                agg_dict['deployed_capital_pct'] = ['mean', 'std']
            if 'total_capital' in df.columns:
                agg_dict['total_capital'] = ['first', 'last']
            
            if agg_dict:
                stats = df.groupby('strategy').agg(agg_dict).round(2)
                st.dataframe(stats, use_container_width=True)
            else:
                st.warning("No numeric columns available for strategy analysis")
        
        # Overall statistics
        st.write("**Overall Statistics**")
        st.dataframe(df.describe().round(2), use_container_width=True)
        
        # Distribution plots
        col1, col2 = st.columns(2)
        
        with col1:
            if 'realized_pnl' in df.columns:
                fig_dist_pnl = px.histogram(
                    df,
                    x='realized_pnl',
                    color='strategy' if 'strategy' in df.columns else None,
                    title='Realized PnL Distribution',
                    marginal='box'
                )
                st.plotly_chart(fig_dist_pnl, use_container_width=True)
        
        with col2:
            if 'deployed_capital_pct' in df.columns:
                fig_dist_deployed = px.histogram(
                    df,
                    x='deployed_capital_pct',
                    color='strategy' if 'strategy' in df.columns else None,
                    title='Deployed Capital % Distribution',
                    marginal='box'
                )
                st.plotly_chart(fig_dist_deployed, use_container_width=True)
    
    with tab4:
        st.subheader("Raw Data")
        
        # Add filters
        col1, col2 = st.columns(2)
        
        with col1:
            num_rows = st.slider('Number of rows to display', 10, len(df), min(100, len(df)))
        
        with col2:
            if 'strategy' in df.columns:
                strategies = df['strategy'].unique().tolist()
                selected_strategies_raw = st.multiselect(
                    'Filter by Strategy',
                    strategies,
                    default=strategies,
                    key='raw_data_strategy'
                )
                df_display = df[df['strategy'].isin(selected_strategies_raw)]
            else:
                df_display = df
        
        st.dataframe(df_display.head(num_rows), use_container_width=True)
        
        # Download button
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name='trading_metrics.csv',
            mime='text/csv',
        )
    
    # Export to Parquet button
    st.divider()
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button('📦 Export to Parquet', use_container_width=True):
            try:
                export_path = Path('exports/metrics.parquet')
                export_path.parent.mkdir(parents=True, exist_ok=True)
                df.to_parquet(export_path)
                st.success(f"✅ Exported {len(df)} records to {export_path}")
            except Exception as e:
                st.error(f"Failed to export: {e}")

else:
    st.warning("⚠️ No data available. Please check your data source configuration.")
    
    st.info("""
    **Getting Started:**
    
    1. **QuestDB Mode:**
       - Start QuestDB: `docker run -d -p 9000:9000 -p 8812:8812 -p 9009:9009 questdb/questdb`
       - Run the trading engine with QuestDB logging enabled
       - Refresh this dashboard
    
    2. **Parquet Mode:**
       - Export metrics from the engine
       - Or manually create `exports/metrics.parquet`
       - Switch to 'Parquet Export' in the sidebar
    """)

# Footer
st.divider()
st.caption("Trading Engine Metrics Dashboard | Built with Streamlit + Plotly")
