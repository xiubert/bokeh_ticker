''' 
Use the ``bokeh serve`` command to run by executing:
    bokeh serve ticker.py
at your command prompt. Then navigate to the URL
    http://localhost:5006/ticker
in your browser.
'''
#if using folder structure can cd to parent dir then:  bokeh serve bokeh_ticker, otherwise `bokeh serve ticker.py`

#for debugging in VSCODE:  put this under configurations in launch.json
# {
#             // first run bokeh serve nameOfscript.py, open browser, then start debug session
#             "name": "Python: Remote Attach:  Bokeh",
#             "type": "python",
#             "request": "attach",
#             "connect": {
#                 "host": "localhost",
#                 "port": 5678
#             },
#             "redirectOutput": true,
#             "pathMappings": [
#                 {
#                     "localRoot": "${workspaceFolder}",
#                     "remoteRoot": "."
#                 }
#             ]
#         }
# this goes in the script
# import ptvsd
# ptvsd.enable_attach(address=('localhost', 5678))
# ptvsd.wait_for_attach() # Only include this line if you always want to attach the debugger

import numpy as np
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, TextInput, Select, RadioButtonGroup, Paragraph
from bokeh.plotting import figure

import pandas as pd
import requests
import datetime

import os
from dotenv import load_dotenv
load_dotenv()

alphaAPI = os.environ.get("ALPHA_VANTAGE_API")

def get_tickerData(sticker,key=alphaAPI):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={sticker}&outputsize=full&apikey={key}'
    r = requests.get(url)
    sdata = r.json()
    assert('Time Series (Daily)' in sdata.keys()),f'{sticker} is not a recognized stock ticker'
    df = pd.DataFrame.from_dict(sdata['Time Series (Daily)']).T
    df['4. close'] = pd.to_numeric(df['4. close'])
    ds = df['4. close']
    ds = ds.rename("closing_price")
    ds.index = pd.to_datetime(ds.index)
    year_opts = ds.index.year.unique()[::-1].astype(str).tolist()

    return ds,year_opts


def get_month_opts(ds,year):
    return ds.index[ds.index.year==int(year)].month_name().unique()[::-1].astype(str).tolist()


def get_month_data(ds,month,year):
    month_closings = ds.iloc[np.logical_and(ds.index.month==datetime.datetime.strptime(month, "%B").month,
                        ds.index.year==int(year))]
    assert(month_closings.shape[0] != 0),f'no data for {month} of {year}'

    return month_closings

# initial data from most recent year and month
init_tickers = ['AMZN','GOOG']
ds,year_opts = get_tickerData(init_tickers[0])
month_opts = get_month_opts(ds,year_opts[-1])
month_closings = get_month_data(ds,month_opts[-1],year_opts[-1])

ds2 = get_tickerData(init_tickers[1])[0]
month_closings2 = get_month_data(ds2,month_opts[-1],year_opts[-1])

source = ColumnDataSource(data=dict(x=month_closings.index, 
            y1=month_closings.values, y2=month_closings2.values))


fig = figure(plot_width=600, plot_height=600,
        x_axis_type = 'datetime',
        x_axis_label = 'Date',
        y_axis_label = 'USD')
fig.line('x', 'y1', source=source,line_color='red',legend_label='1',name='ticker1')
fig.line('x', 'y2', source=source,line_color='blue',legend_label='2',name='ticker2')
fig.xaxis[0].formatter = DatetimeTickFormatter(days="%m/%d")

# set legend label visibility for second renderer to False
fig.legend.items[1].visible = False
fig.select(name="ticker2").visible = False


#WIDGETS
text_input = TextInput(value=init_tickers[0], title="Enter stock ticker symbol:")
year_menu = Select(title='Choose Year:', value=year_opts[-1], options=year_opts)
month_menu = Select(title='Choose Month:', value=month_opts[-1], options=month_opts)
radio_button_group = RadioButtonGroup(labels=[f'{i+1}: {tick}' for i,tick in enumerate(init_tickers)], active=0)
pgraph = Paragraph(text='',width=400, height=100)

#WIDGET CALLBACKS
def update_fig_ticker(attrname, old, new_ticker):
    global ds,ds2
    radio_active = radio_button_group.active
    if new_ticker != radio_button_group.labels[radio_active][3::]:
        if new_ticker != radio_active == 0:   
            try:   
                ds,year_opts = get_tickerData(new_ticker)
                radio_button_group.labels[radio_active] = f'{radio_active+1}: {new_ticker}'

                old_year=year_menu.value
                old_month=month_menu.value
                year_menu.options = year_opts
                if np.isin(old_year,year_opts):
                    year_menu.value = old_year
                else:
                    year_menu.value = year_opts[0]
                
                month_opts = get_month_opts(ds,year_menu.value)
                month_menu.options = month_opts
                if np.isin(old_month,month_opts):
                    month_menu.value = old_month
                else:
                    month_menu.value = month_opts[0]

                month_closings = get_month_data(ds,month_menu.value,year_menu.value)
                #do this with the rest:
                try:
                    month_closings2 = get_month_data(ds2,month_menu.value,year_menu.value)
                    source.data = dict(x=month_closings.index, y1=month_closings.values,y2=month_closings2.values)
                except AssertionError:
                    source.data = dict(x=month_closings.index, y1=month_closings.values)
            except AssertionError:
                pgraph.text = f'{new_ticker} is not a recognized stock ticker'

            

        elif radio_active == 1:
            try:
                ds2 = get_tickerData(new_ticker)[0]
                radio_button_group.labels[radio_active] = f'{radio_active+1}: {new_ticker}'

                try:
                    month_closings = get_month_data(ds2,month_menu.value,year_menu.value)
                    source.data['y2'] = month_closings.values
                    corcalc = np.corrcoef(source.data['y1'],source.data['y2'])
                    pgraph.text = f'Correlation: {corcalc[0][1]:.2f}'
                except AssertionError:
                    source.data = {a: source.data[a] for a in ['x','y1']}
                    pgraph.text = f'No data for {new_ticker} in {month_menu.value} of {year_menu.value}'
            except AssertionError:
                pgraph.text = f'{new_ticker} is not a recognized stock ticker'


def year_change(attrname, oldyr, newyr):
    global ds,ds2
    old_month=month_menu.value
    month_opts = get_month_opts(ds,newyr)
    month_menu.options = month_opts
    if np.isin(old_month,month_opts):
        month_menu.value = old_month
    else:
        month_menu.value = month_opts[0]

    month_closings = get_month_data(ds,month_menu.value,newyr)
    try:
        month_closings2 = get_month_data(ds2,month_menu.value,newyr)
        source.data = dict(x=month_closings.index, y1=month_closings.values,y2=month_closings2.values)
    except AssertionError:
        source.data = dict(x=month_closings.index, y1=month_closings.values)

def month_change(attrname, oldmo, newmo):
    global ds,ds2
    month_closings = get_month_data(ds,newmo,year_menu.value)

    try:
        month_closings2 = get_month_data(ds2,newmo,year_menu.value)
        source.data = dict(x=month_closings.index, y1=month_closings.values,y2=month_closings2.values)
    except AssertionError:
        source.data = dict(x=month_closings.index, y1=month_closings.values)

def radio_change(new):
    # print(f'radio option {new} or as str {str(new)}')
    text_input.value = radio_button_group.labels[new][3::]
    if new==0:
        fig.select(name="ticker2").visible = False
        fig.legend.items[1].visible = False
        year_menu.visible = True
        month_menu.visible = True
        pgraph.text = ''

    elif new==1:
        fig.legend.items[new].visible = True
        fig.select(name="ticker2").visible = True
        year_menu.visible = False
        month_menu.visible = False

        if len(source.data)>2:
            corcalc = np.corrcoef(source.data['y1'],source.data['y2'])
            pgraph.text = f'Correlation: {corcalc[0][1]:.2f}'
        else:
            pgraph.text = f'No data for {text_input.value} in {month_menu.value} of {year_menu.value}'

#SEND WIDGET CALLBACKS
text_input.on_change('value', update_fig_ticker)
year_menu.on_change('value', year_change)
month_menu.on_change('value', month_change)
radio_button_group.on_click(radio_change)

# Set up layouts and add to document
inputs = column(radio_button_group,text_input,year_menu,month_menu,pgraph)

curdoc().add_root(row(inputs, fig, width=800))
curdoc().title = "TICKER"