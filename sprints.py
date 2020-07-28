# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 19:25:28 2020

@author: charl
"""

from MetricaUtils import Reformat, VelocityCalc, RemoveInactive, GiveNames
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng() # define numpy random number generator


imported_home = pd.read_csv('data/Sample_Game_1_RawTrackingData_Home_Team.csv', skiprows=2) # ignore first 2 unneeded rows on inport
imported_away = pd.read_csv('data/Sample_Game_1_RawTrackingData_Away_Team.csv', skiprows=2)

timestep = imported_home["Time [s]"].iloc[1] - imported_home["Time [s]"].iloc[0] # find timestep of imported data from csv

pitch_xdim = 105 # pitch dimension in metres
pitch_ydim = 68

frames_per_sample = 5 # how often will we sample the data - e.g. 5 = sample every 5 frames
sampled_timestep= frames_per_sample * timestep

tracking_home_sampled = imported_home.iloc[::frames_per_sample] # keep every 5th row
tracking_away_sampled = imported_away.iloc[::frames_per_sample]

tracking_home = Reformat(tracking_home_sampled) # set to use sampled version to load into DB
tracking_away = Reformat(tracking_away_sampled)

tracking_home = GiveNames(tracking_home) # replpace Player1 placeholders etc with generated names 
tracking_away = GiveNames(tracking_away)

home_dict = VelocityCalc(tracking_home, pitch_xdim, pitch_ydim, sampled_timestep) # perform velocity and acceleration calcs
away_dict = VelocityCalc(tracking_away, pitch_xdim, pitch_ydim, sampled_timestep)
  
home_dict = RemoveInactive(home_dict)
away_dict = RemoveInactive(away_dict)


# plot velocity-time breakdowns for each player - where velocities defined by:
# https://www.frontiersin.org/articles/10.3389/fphys.2017.00432/full

# Standing <0.17m/s
# Walking 0.17 to 2
# Jogging 2 to 4
# Running 5 to 5.5
# High-intensity > 5.5


standing = 0.17 # max velocity cut-off
walking = 2
jogging = 4
running = 5.5
high_intense = 12 # approx top speed for professional sprinter - values above this likely to be error

bin_edges = [0,standing, walking, jogging, running, high_intense]


keys_list = list(home_dict.keys())
players = [i for i in keys_list if i != 'Ball'] # remove ball from key list to get players only

fig, axes = plt.subplots(nrows=4, ncols=4, figsize=(22,22))

fig.suptitle('Categorised Player On-pitch Movement Intensity', fontsize = 26)

for ax, player in zip(axes.flat, players):
    ax.set_title(player, fontsize = 16)
    data = home_dict[player]['vel']
    h,e = np.histogram(data, bins=bin_edges)
    h = h / sum(h)
    ax.bar(range(len(bin_edges)-1),h, width=1, color = tuple(rng.random(size=3)))
    ax.set_xticks(range(len(bin_edges)-1))
    ax.set_xticklabels(['Standing', 'Walking', 'Jogging', 'Running', 'High Intensity'])
    ax.set_ylabel('% of time on pitch')
    ax.set_xlabel('Effort Category') 
    ax.set_ylim(0,1)

        
# remove any unused axes -  TODO: make this dynamic based on number of players 
axes[3,3].set_axis_off()
axes[3,2].set_axis_off()

fig.tight_layout()
fig.subplots_adjust(top=0.92) # personal preference for main title spacing

plt.show()

