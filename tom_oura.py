from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import streamlit as st

def add_weeks(df_input, date_col):
    df_input['dt_date'] = pd.to_datetime(df_input[date_col])
    df_input["dayofweek"] = df_input.dt_date.dt.weekday
    df_input['week'] = df_input['dt_date'].apply(lambda x: (x - timedelta(days=x.dayofweek)))
    df_input['month'] = df_input['dt_date'].apply(lambda x: (x.to_period('M')))
    return df_input

def agg_percentile_data(df_input, cols_to_agg, groupby_cols):
    subset_of_cols = list(cols_to_agg + groupby_cols)
    df = df_input[subset_of_cols].groupby(groupby_cols).describe().stack(level=0)[['25%', '50%', '75%', 'mean']].reset_index().rename(columns={"level_2":"p", "level_1":"agg_metric"})
    df = df.loc[lambda x: x.agg_metric.isin(cols_to_agg)]
    df[groupby_cols[0]+'_str'] = df[groupby_cols].astype(str)
    return df
def agg_metrics(df_input, date_col, cols_to_agg, groupby_cols):
  df = add_weeks(df_input, date_col)
  df = agg_percentile_data(df, cols_to_agg,groupby_cols)
  df['temporal_rank'] = df.groupby('agg_metric')[groupby_cols[0]+'_str'].rank('max', ascending=False)
  df = df.sort_values(by = ['agg_metric','temporal_rank'], ascending = True)
  return df


df = pd.read_csv('https://raw.githubusercontent.com/tzidar/tom_streamlit_oura/main/sleep_data_2022_12_18.csv')
df = df.drop(columns=['Unnamed: 0'])
print(df.columns)
df['rem_hours'] = df['rem'] / 60 / 60
# df['hrv'] = df['hr_5min'].var()
# df['hr_5min'].apply(lambda x: (x.var()))
# df.dtypes
# a = df.rmssd_5min[0].strip('[').strip(']').strip(',').replace(' ','').split(',')
# b = [int(x) for x in a]
# np.mean(b)

# np.mean(b/np.std(b))

# np.mean(b)
# np.var(b)

df_weekly_snapshot = agg_metrics(df_input= df, date_col='summary_date', cols_to_agg=['rem_hours','hr_average','wake_up_count','rmssd'], groupby_cols=['week'])
df_monthly_snapshot = agg_metrics(df_input= df, date_col='summary_date', cols_to_agg=['rem_hours','hr_average','wake_up_count','rmssd'], groupby_cols=['month'])
df_weekly_snapshot['lag_50%_1'] = df_weekly_snapshot['50%'].shift(-1)
df_weekly_snapshot['pct_change'] = (df_weekly_snapshot['50%']-df_weekly_snapshot['lag_50%_1'])/df_weekly_snapshot['lag_50%_1']
df_last_period = df_weekly_snapshot.loc[lambda df: df.temporal_rank ==1 ]

hr_pct_wow = round(df_last_period.loc[lambda x: x['agg_metric'] == 'hr_average'][['pct_change']].iloc[0].values[0]*100,2)
median_hr = round(df_last_period.loc[lambda x: x['agg_metric'] == 'hr_average'][['50%']].iloc[0].values[0],2)
rem_pct_wow = round(df_last_period.loc[lambda x: x['agg_metric'] == 'rem_hours'][['pct_change']].iloc[0].values[0]*100,2)
median_rem = round(df_last_period.loc[lambda x: x['agg_metric'] == 'rem_hours'][['50%']].iloc[0].values[0],2)
wu_pct_wow = round(df_last_period.loc[lambda x: x['agg_metric'] == 'wake_up_count'][['pct_change']].iloc[0].values[0]*100,2)
median_wu = round(df_last_period.loc[lambda x: x['agg_metric'] == 'wake_up_count'][['50%']].iloc[0].values[0],2)

df_wakeups = df_weekly_snapshot.loc[lambda x: x['agg_metric'] == 'wake_up_count'].rename(columns={"50%":"Median"})
df_monthly_wake_ups = df_monthly_snapshot.loc[lambda x: x['agg_metric'] == 'wake_up_count'].rename(columns={"50%":"Median"})
df_monthly_rem = df_monthly_snapshot.loc[lambda x: x['agg_metric'] == 'rem_hours'].rename(columns={"50%":"Median"})
df_hrv_monthly = df_monthly_snapshot.loc[lambda x: x['agg_metric'] == 'rmssd'].rename(columns={"50%":"Median"})



st.header("Tom's Oura Data")
st.subheader('Median Weekly Snapshot')
col1, col2, col3 = st.columns(3)
col1.metric("Median Daily Heart Rate", median_hr, str(hr_pct_wow)+'%')
col2.metric("REM", median_rem, str(rem_pct_wow)+'%')
col3.metric("Wake up Count",median_wu , str(wu_pct_wow)+'%',delta_color = 'inverse')
#col4.metric("Wake up Count", "86%", "4%")

st.subheader('Trending Wakeups per Night')
st.bar_chart(
  data=df_monthly_wake_ups,
  x='month_str',
  y='Median'
)

st.subheader('Trending HRV')
st.bar_chart(
  data=df_hrv_monthly,
  x='month_str',
  y='Median'
)

st.subheader('Trending REM')
st.bar_chart(
  data=df_monthly_rem,
  x='month_str',
  y='Median'
)


df_2022_july = df.loc[lambda df: df.summary_date > '2022-06-01']


st.subheader('Does High Activity Hit my HRV')
st.line_chart(
  data=df.loc[lambda df: df.summary_date > '2022-06-01'],
  x='summary_date',
  y=['high','rmssd']
)

st.dataframe(df_2022_july[['high','medium','low','cal_active','inactive','rmssd']].corr()[:1])


st.subheader('Temperature & Sleep')
st.line_chart(
  data=df.loc[lambda df: df.summary_date > '2022-06-01'],
  x='summary_date',
  y=['temperature_deviation','score_total']
)


df_temp = df_2022_july[['temperature_deviation','temperature_trend_deviation','temperature_delta','score_total','breath_average','efficiency']].corr()[:1]
st.dataframe(df_temp)
st.text('Skin temperature deviation from the long-term temperature average.')



st.subheader('Granular Data')
st.dataframe(df)

st.subheader('Correlations..')
st.dataframe(df_2022_july.corr().style.highlight_max(axis=0))

st.caption('Oura API Documentation:https://cloud.ouraring.com/docs/sleep')
st.caption('HRV explanation:https://support.ouraring.com/hc/en-us/articles/360025441974-An-Introduction-to-Heart-Rate-Variability')
# 

# df_rand = pd.DataFrame(
#    np.random.randn(10, 5),
#    columns=('col %d' % i for i in range(5)))



# chart_data = pd.DataFrame(
#     np.random.randn(20, 3),
#     columns=["a", "b", "c"])

# st.bar_chart(chart_data)

# st.bar_chart(
#   # Enter your data below! Usually this is not a dict, but a Pandas Dataframe.,
#   data={'time': [0, 1, 2, 3, 4, 5, 6], 'stock_value': [100, 200, 150, 300, 450, 500, 600]},
#   x='time',
#   y='stock_value'
# )