""" module creates the dashboard '/insights' page """

# -*- coding: utf-8 -*-
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objects as go

# path to Excel sheet used for creating stas dataframes
PATH_TO_EXCEL_SHEET = 'tools/dataset_metrics/metrics.xlsx'

def _get_df_from_excel_sheet(sheet_name):
    """ private helper function used to read excel sheets and 
        create dataframes from the specified sheet"""

    return pd.read_excel(PATH_TO_EXCEL_SHEET, sheet_name, engine='openpyxl')


def dataset_by_domain_table():
    """ function used to create the Table component which displays 
    the number of pages/datasets obtained from each domain """

    # get the dataframe from the excel sheet
    df = _get_df_from_excel_sheet('PAGE COUNT (DATOPIAN)')
    # create the DataTable
    return dash_table.DataTable(
                                id='dataset_by_domain_table',
                                columns=[{"name": i, "id": i} \
                                    if i != "page count" else \
                                        {"name": "dataset count", "id": i} \
                                            for i in df.columns],
                                data=df.to_dict('records'),
                                sort_action='native',
                                style_cell={'textAlign': 'left', 
                                            'whiteSpace': 'normal'},
                                #fixed_rows={ 'headers': True, 'data': 0 },
                                #virtualization=True,
                                style_cell_conditional=[
                                                        {'if': {'column_id': 'domain'},
                                                        'width': '70%',
                                                        'textAlign': 'right'},
                                                        {'if': {'column_id': 'page count'},
                                                        'width': '30%'}],
                                style_table={
                                                'maxHeight': '300px',
                                                'maxWidth': '100%',
                                                'overflowY': 'scroll',
                                                'overflowX': 'hidden',
                                                'margin': 0,
                                                'padding': 0
                                                })


def dataset_by_domain_bar():
    """ function creates a bar chart which displays the 
    number of pages/datasets per domain """
    # the the dataframe from the Excel sheet
    df = _get_df_from_excel_sheet('PAGE COUNT (DATOPIAN)')
    # create the bar chart using the created dataframe
    return dcc.Graph(
        id='dataset_by_domain_graph',
        figure={
            'data': [
                        {'x': df['domain'], 'y': df['page count'], 'type': 'bar'}
                    ],
            'layout': {
                'title': 'Datasets By Domain'
            }
        }
    )
    

def resources_by_domain_table():
    """ function is used to create DataTable containing
    the number of resources/domains """

    # to perform this tasks, we need to collect stas from 2 different sheets
    # and unifiy it into one dataframe
    
    # get the resources collected from the datopian end of the air-datopian intersect
    df = _get_df_from_excel_sheet('RESOURCE COUNT PER DOMAIN (DATOPIAN-AIR INTERSECTION)')

    # create a dataframe to hold the necessary info we use for this task
    working_df1 = pd.DataFrame(columns=['domain'])
    working_df1['domain'] = df['domain']
    working_df1['resource count'] = df['resource count_datopian']

    # get the resources from the DAtopian only resource count
    df = _get_df_from_excel_sheet('RESOURCE COUNT PER DOMAIN (DATOPIAN ONLY)')
    working_df2 = pd.DataFrame(columns=['domain'])
    working_df2['domain'] = df['domain']
    working_df2['resource count'] = df['resource count']

    # concatenate the 2 dataframes
    working_df1 = pd.concat([working_df1,
                              working_df2], axis='index', ignore_index=True)
    # return the created DataTable
    return dash_table.DataTable(
                                id='resource_by_domain_table',
                                columns=[{"name": i, "id": i} for i in working_df1.columns],
                                data=working_df1.to_dict('records'),
                                sort_action='native',
                                style_cell={'textAlign': 'left', 
                                            'whiteSpace': 'normal'},
                                #fixed_rows={ 'headers': True, 'data': 0 },
                                #virtualization=True,
                                style_cell_conditional=[
                                        {'if': {'column_id': 'domain'},
                                        'width': '70%', 'textAlign': 'right'},
                                        {'if': {'column_id': 'resource count'},
                                        'width': '30%'}],
                                style_table={
                                                'maxHeight': '300px',
                                                'maxWidth': '100%',
                                                'overflowY': 'scroll',
                                                'overflowX': 'hidden',
                                                'margin': 0,
                                                'padding': 0
                                                })

def resources_by_domain_pie():
    """" function is used to created a pie chart showing
    the number of resources gotten per domain """

    # this function uses a concatenation of 2 different excel sheets and dataframes
    df = _get_df_from_excel_sheet('RESOURCE COUNT PER DOMAIN (DATOPIAN-AIR INTERSECTION)')
    working_df1 = pd.DataFrame(columns=['domain'])
    working_df1['domain'] = df['domain']
    working_df1['resource count'] = df['resource count_datopian']

    df = _get_df_from_excel_sheet('RESOURCE COUNT PER DOMAIN (DATOPIAN ONLY)')
    working_df2 = pd.DataFrame(columns=['domain'])
    working_df2['domain'] = df['domain']
    working_df2['resource count'] = df['resource count']

    # concatenate the 2 dataframes
    working_df1 = pd.concat([working_df1,
                              working_df2], axis='index', ignore_index=True)

    # return the pie chart
    return dcc.Graph(
        id='resources_by_domain_pie',
        figure=go.Figure(data=[go.Pie(labels=working_df1['domain'],
                             values=working_df1['resource count'], 
                             title={'text': 'Resources By Domain', 'font': {'size': 16}, 'position': 'bottom right'})])
    )

def generate_split_layout():
    """" function generates the latyout for this page """

    return html.Div(children=[
                                html.Div([
                                            html.H1('Domain Dataset Stats',
                                            style={'text-align': 'center',
                                                   'font-weight': 'bold'}),
                                         ],
                                         style={'width': '100%', 
                                                'display': 'inline-block', 
                                                'vertical-align': 'middle'}),
                                html.Div([
                                            dataset_by_domain_table()
                                         ],
                                         style={'width': '45%', 
                                                'display': 'inline-block',
                                                'vertical-align': 'middle', 
                                                'overflow-x': 'visible'}
                                        ),

                                html.Div([],
                                        style={'width': '5%', 
                                               'display': 'inline-block', 
                                               'vertical-align': 'middle'}
                                        ),
                                html.Div([
                                            dataset_by_domain_bar()
                                         ], 
                                         style={'width': '50%', 
                                                'display': 'inline-block', 
                                                'vertical-align': 'middle'}),

                                html.Hr(),

                                html.Div([
                                            html.H1('Domain Resources Stats', 
                                                    style={'text-align': 'center', 
                                                           'font-weight': 'bold'}),
                                         ],
                                         style={'width': '100%',
                                                'display': 'inline-block', 
                                                'vertical-align': 'middle'}
                                        ),
                                html.Div([
                                            resources_by_domain_table()
                                         ],
                                         style={'width': '45%', 
                                                'display': 'inline-block', 
                                                'vertical-align': 'middle', 
                                                'overflow-x': 'visible'}
                                        ),

                                html.Div([],
                                         style={'width': '5%', 
                                                'display': 'inline-block', 
                                                'vertical-align': 'middle'}
                                        ),
                                html.Div([
                                            resources_by_domain_pie()
                                         ], 
                                         style={'width': '50%', 
                                                'display': 'inline-block', 
                                                'vertical-align': 'middle'}
                                        ),

                                html.Hr()

    

])


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = generate_split_layout

if __name__ == '__main__':
    app.run_server(debug=False, dev_tools_hot_reload=True, host='0.0.0.0')
