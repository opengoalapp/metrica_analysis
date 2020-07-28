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

# function to remove data points where implied velocity is > 12m/s (limit of elite human sprinting)

def RemoveImplausible(team_dict):
    
    for player in team_dict:
        team_dict[player] = team_dict[player][team_dict[player]['vel'] <= 12]
    return team_dict 


# function to generate start and stop frames for posssessions for each team
    
def GetPossessionWindows(event_data, home_dict, away_dict):
    
    event_data['team_int'] = event_data['team'].map({'Home': 1, 'Away': 0}) # binarize so we can do a diff to detect change of possession
    
    pos_change_1 = event_data['team_int'].diff()[event_data['team_int'].diff() ==-1].index.values
    pos_change_2 = event_data['team_int'].diff()[event_data['team_int'].diff() ==1].index.values
    
    data = {'start': pos_change_2, 'end': pos_change_1}
    nonko_team_pos = pd.DataFrame(data = data) # data for team who receives ball on first possession change
    nonko_team_pos['end'] = nonko_team_pos['end']-1
    
    pos_change_1 = np.insert(pos_change_1,0,0) # insert 0 at start of array for team who starts with ball
    pos_change_2 = np.append(pos_change_2, len(event_data)-1) # add last index to the end of the array as this will be the pos end at final whistle
    data = {'start': pos_change_1, 'end': pos_change_2}
    ko_team_pos = pd.DataFrame(data = data) # data for team who kicks off
    ko_team_pos['end'] = ko_team_pos['end']-1
    
    #if team in pos at half end kicks off 2nd half then any time on the clock accumulated over half time will count as a possession time
    #maybe strip it after  - but shouldn't matter as time when ball is inactive is stripped out   
    
    ko_team_pos_name = event_data['team'].iloc[0] # TODO: if using metrica data with actual team names will need a one liner to convert actual team names to Home and Away
     # lookup start and end frames
    teams = [ko_team_pos,nonko_team_pos]
    
    for team in teams:
        
        start_frames = []
        end_frames = []
        
        for row in team.itertuples(index=False):
            start_frame = event_data['start_frame'].iloc[row[0]]
            end_frame = event_data['start_frame'].iloc[row[1]]
            
            start_frames.append(start_frame)
            end_frames.append(end_frame)
        
        team['start_frame'] = start_frames
        team['end_frame'] = end_frames
     
    dicts = {'Home':home_dict, 'Away':away_dict}    
    
    for team_dict in dicts.items():
        
        if team_dict[0] == 'Home': # get key of active dict
            active_team = 'Home'
        else:
            active_team = 'Away'
    
        for player in team_dict[1]:
        
            team_dict[1][player]['in_pos'] = 0
            team_dict[1][player]['opp_in_pos'] = 0
            
            if ko_team_pos_name == active_team:
                
                for row in ko_team_pos.itertuples(index=False):
                    team_dict[1][player].loc[(team_dict[1][player].frame >= row[2]) &(team_dict[1][player].frame <= row[3]), 'in_pos'] = 1
                    
                for row in nonko_team_pos.itertuples(index=False):
                    team_dict[1][player].loc[(team_dict[1][player].frame >= row[2]) &(team_dict[1][player].frame <= row[3]), 'opp_in_pos'] = 1
                    
            else:
            
                for row in nonko_team_pos.itertuples(index=False):
                    team_dict[1][player].loc[(team_dict[1][player].frame >= row[2]) &(team_dict[1][player].frame <= row[3]), 'in_pos'] = 1
                    
                for row in ko_team_pos.itertuples(index=False):
                    team_dict[1][player].loc[(team_dict[1][player].frame >= row[2]) &(team_dict[1][player].frame <= row[3]), 'opp_in_pos'] = 1    
        
    
    
    home_dict = dicts['Home']
    away_dict = dicts['Away']
    
    return home_dict, away_dict    
