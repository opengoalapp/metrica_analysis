# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 20:03:11 2020

@author: charl
"""

import pandas as pd
import names
import numpy as np


# Reformat dataframe output from pd.read_csv() on an Metrica open tracking data CSV file
# into a more user/database friendly format

def Reformat(data): # Input - a dataframe, Output - a reformatted dataframe

    cols = list(data) # rename unamed columns with preceding column + "_y" or column + "_x"
    for x in cols:
        pos = cols.index(x)
        
        if pos <= 2:
            continue
        
        elif "Unnamed" in x:
            data.rename(columns={x: cols[pos-1]+"_y"}, inplace=True)
            
        else:
            data.rename(columns={x: cols[pos]+"_x"}, inplace=True)
        
    
    melted = pd.melt(data, id_vars=['Period', 'Frame','Time [s]'], var_name = 'player')
    melted = melted.sort_values(['Frame','player'])
    
    melted_locs = pd.DataFrame({'x_loc':melted['value'].iloc[::2].values, 'y_loc':melted['value'].iloc[1::2].values})
    
    melted = melted.iloc[::2]
    
    melted = melted.reset_index(drop=True) # remember to reset index so you can do a concat on cols
    melted_locs = melted_locs.reset_index(drop=True)
    
    
    melted = pd.concat([melted, melted_locs], axis=1)
    
    melted = melted.drop(['value'], axis = 1)
    
    player = []
    for x in melted['player']:
        x = x[:-2]
        player.append(x)
    
    melted['player'] = player 
    
    melted = melted.rename(columns={'Period': 'period', 'Frame': 'frame', 'Time [s]': 'time'})
    return melted




# function to assign random names to "Player X" values in Metrica open data - can set either male or female names

def GiveNames(team_data): # Input - a Reformatted (see above) team dataframe, Output - the same dataframe but with player names replaced
    for player in set(team_data.loc[:,"player"]):
        if player != 'Ball':
            team_data.loc[:,"player"] = team_data.loc[:,"player"].replace(player,names.get_full_name(gender = 'female'))
    
    return team_data 



# function to calculate veloicty and acceleration values for each player at each time step and return dictionary of player data

def VelocityCalc(team_data, pitch_xdim, pitch_ydim, sampled_timestep): # Input - a Reformatted (see above) team dataframe, pitch x dimension in metres,
                                                                       # pitch y dimension in metres, timestep of data
                                                                       # Output - Dataframe with velocty and acceleration data columns appended

    team_dict = {} # create empty dictionary which will contain data for each player
    
    
    for player in set(team_data.loc[:,"player"]):
        player_df = team_data[team_data["player"] == player]
        
        player_df.loc[:,"x_diff"] = player_df.loc[:,"x_loc"].diff(-1)*pitch_xdim # get actual value in metres and get difference in x_loc from subsequent frame
        player_df.loc[:,"x_diff"] = player_df.loc[:,"x_diff"].shift(1)
        player_df.loc[:,"x_vel"] = player_df.loc[:,"x_diff"] / sampled_timestep # dx/dt
        
        player_df.loc[:,"y_diff"] = player_df.loc[:,"y_loc"].diff(-1)*pitch_ydim # get difference in x_loc from subsequent frame
        player_df.loc[:,"y_diff"] = player_df.loc[:,"y_diff"].shift(1)
        player_df.loc[:,"y_vel"] = player_df.loc[:,"y_diff"] / sampled_timestep # dy/dt
        
        player_df.loc[:,"vel"] = np.sqrt((player_df.loc[:,"x_vel"]**2) + (player_df.loc[:,"y_vel"]**2)) # get velocity magnitude
        player_df.loc[:,"acc"] = player_df.loc[:,"vel"].diff(1) / sampled_timestep # d2y/dx2
        
        
        team_dict[player] = player_df # write to dictionary
        
    return team_dict 


# function to remove "dead" time when the ball isn't in play or can't be measured - note you might not always want to remove this data

def RemoveInactive(team_dict): # Input - a dictionary of a team's player data dataframes, # Output - the same dictionary but with ball inactive time entries removed

    # create mask where ball is not active, and remove relevant rows from player data
    inactive_mask = team_dict['Ball'].loc[:,'x_loc'].isnull()

    # all data has same length, is in same chronological order so we can apply mask as is
    for player in team_dict:
        team_dict[player].loc[:,'x_loc'] = np.where(inactive_mask,float('NaN') , team_dict[player].loc[:,'x_loc'])
        team_dict[player] = team_dict[player].drop(team_dict[player][team_dict[player]['x_loc'].isnull()].index)
    
    return team_dict  