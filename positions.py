# -*- coding: utf-8 -*-
"""
Created on Sat Jul 18 20:12:47 2020

@author: charl
"""

from MetricaUtils import Reformat, VelocityCalc, RemoveInactive, GiveNames, RemoveImplausible,  GetPossessionWindows
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from draw_pitch import draw_pitch

rng = np.random.default_rng() # define numpy random number generator


imported_home = pd.read_csv('data/Sample_Game_1_RawTrackingData_Home_Team.csv', skiprows=2) # ignore first 2 unneeded rows on inport
imported_away = pd.read_csv('data/Sample_Game_1_RawTrackingData_Away_Team.csv', skiprows=2)
imported_events = pd.read_csv('data/Sample_Game_1_RawEventsData.csv')

timestep = imported_home["Time [s]"].iloc[1] - imported_home["Time [s]"].iloc[0] # find timestep of imported data from csv

pitch_xdim = 105 # pitch dimension in metres
pitch_ydim = 68

frames_per_sample = 5 # how often will we sample the data - e.g. 5 = sample every 5 frames
sampled_timestep= frames_per_sample * timestep

tracking_home = imported_home.iloc[::frames_per_sample] # keep every 5th row
tracking_away = imported_away.iloc[::frames_per_sample]

tracking_home = Reformat(tracking_home) # reformat into more user friendly form
tracking_away = Reformat(tracking_away)

tracking_home = GiveNames(tracking_home) # replpace Player1 placeholders etc with generated names 
tracking_away = GiveNames(tracking_away)

home_dict = VelocityCalc(tracking_home, pitch_xdim, pitch_ydim, sampled_timestep) # perform velocity and acceleration calcs
away_dict = VelocityCalc(tracking_away, pitch_xdim, pitch_ydim, sampled_timestep)
  
home_dict = RemoveInactive(home_dict)
away_dict = RemoveInactive(away_dict)

# clean data a bit by removing entires where implied velocity is >12m/s as this suggests an error

home_dict = RemoveImplausible(home_dict)
away_dict = RemoveImplausible(away_dict)

# add team possession info for each player in the match
home_dict, away_dict = GetPossessionWindows(imported_events, home_dict, away_dict)



#########################################################################################
# now do some plotting based on new possession flags

# get average position for away team, 1st half

half = 1
avg_posns_lst = []
players = []
for key, player in away_dict.items():
    if key == 'Ball':
        continue
    grouped = player.groupby(['period']).mean().loc[:,['x_loc','y_loc']]
    
    if half in grouped.index:
        players.append(key)
        avg_posns_lst.append(grouped.loc[half,:]) # note loc not iloc
        
        
avg_posns_frame = pd.DataFrame(avg_posns_lst)     
avg_posns_frame['player'] = players
avg_posns_frame['player_no'] = list(range(12,12+len(players))) # give players fake numbers starting from 12 for simpler plot labellng
avg_posns_frame = avg_posns_frame.set_index('player_no')    
  
 # plot all positions
fig = plt.figure(frameon=False)
im1 = draw_pitch("#4e4170","#faf0e6","v","full")

PITCH_X = 68 # constant dims of the pitch drawing function
PITCH_Y = 105                 
                 
x = avg_posns_frame['y_loc']*PITCH_X 
y = avg_posns_frame['x_loc']*PITCH_Y
       
im2 = plt.scatter(x, y, alpha = 0.8, s = 500, zorder = 2) # 0,0 is top left so we can invert axes for vertical layout            

#create labels
surnames = [i.split(' ', 1)[1] for i in players]

#for i, txt in enumerate(list(avg_posns_frame.index)):
#    plt.annotate(txt, (x[i], y[i]-5), size = 12, ha = 'center', va = 'center', color = '#D8E2E3')

for number in list(avg_posns_frame.index):
    plt.annotate(number, (x[number], y[number]), size = 12, ha = 'center', va = 'center', color = '#D8E2E3')

plt.show()    

#plot all positions by possession

# get average position for away team in possession, 1st half

half = 1
avg_posns_lst_ip = []
players = []
for key, player in away_dict.items():
    if key == 'Ball':
        continue
    grouped = player.groupby(['period','in_pos']).mean().loc[:,['x_loc','y_loc']]
    
    if half in grouped.index:
        players.append(key)
        avg_posns_lst_ip.append(grouped.loc[(half,1),:]) # 1st half, own team in posession = 1
        
        
avg_posns_frame_ip = pd.DataFrame(avg_posns_lst_ip)     
avg_posns_frame_ip['player'] = players
avg_posns_frame_ip['player_no'] = list(range(12,12+len(players)))
avg_posns_frame_ip = avg_posns_frame_ip.set_index('player_no')    


# get average position for away team opponent in possession, 1st half

half = 1
avg_posns_lst_op = []
players = []
for key, player in away_dict.items():
    if key == 'Ball':
        continue
    grouped = player.groupby(['period','opp_in_pos']).mean().loc[:,['x_loc','y_loc']]
    
    if half in grouped.index:
        players.append(key)
        avg_posns_lst_op.append(grouped.loc[(half,1),:]) # 1st half, opp team in posession = 1
        
        
avg_posns_frame_op = pd.DataFrame(avg_posns_lst_op)     
avg_posns_frame_op['player'] = players
avg_posns_frame_op['player_no'] = list(range(12,12+len(players)))
avg_posns_frame_op = avg_posns_frame_op.set_index('player_no')  
    

 # plot positions in possession
fig = plt.figure(frameon=False)
im1 = draw_pitch("#4e4170","#faf0e6","v","full")

PITCH_X = 68 # constant dims of the pitch drawing function
PITCH_Y = 105                 
                 
x = avg_posns_frame_ip['y_loc']*PITCH_X 
y = avg_posns_frame_ip['x_loc']*PITCH_Y
       
im2 = plt.scatter(x, y, alpha = 0.8, s = 500, zorder = 2) # 0,0 is top left so we can invert axes for vertical layout            

#create labels
surnames = [i.split(' ', 1)[1] for i in players]

#for i, txt in enumerate(surnames):
#    plt.annotate(txt, (x[i], y[i]), size = 12, ha = 'center', va = 'center', color = '#D8E2E3')
                 
for number in list(avg_posns_frame.index):
    plt.annotate(number, (x[number], y[number]), size = 12, ha = 'center', va = 'center', color = '#D8E2E3')                 

plt.show()    

 # plot positions opp in possession
fig = plt.figure(frameon=False)
im1 = draw_pitch("#4e4170","#faf0e6","v","full")

PITCH_X = 68 # constant dims of the pitch drawing function
PITCH_Y = 105                 
                 
x = avg_posns_frame_op['y_loc']*PITCH_X 
y = avg_posns_frame_op['x_loc']*PITCH_Y
       
im2 = plt.scatter(x, y, alpha = 0.8, s = 500, zorder = 2) # 0,0 is top left so we can invert axes for vertical layout            

#create labels
surnames = [i.split(' ', 1)[1] for i in players]

#for i, txt in enumerate(surnames):
#    plt.annotate(txt, (x[i], y[i]), size = 12, ha = 'center', va = 'center', color = '#D8E2E3')
                 
for number in list(avg_posns_frame.index):
    plt.annotate(number, (x[number], y[number]), size = 12, ha = 'center', va = 'center', color = '#D8E2E3')                 

plt.show()    


