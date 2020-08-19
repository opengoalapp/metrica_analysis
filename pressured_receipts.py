# -*- coding: utf-8 -*-
"""

@author: charl
"""

# code to go alongside Applied Tracking: Pressure - https://www.opengoalapp.com/tracking-pressure

from MetricaUtils import Reformat
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap
import matplotlib
from mplsoccer.pitch import Pitch

imported_home = pd.read_csv('data/Sample_Game_1_RawTrackingData_Home_Team.csv', skiprows=2) # ignore first 2 unneeded rows on inport
imported_away = pd.read_csv('data/Sample_Game_1_RawTrackingData_Away_Team.csv', skiprows=2)
imported_events = pd.read_csv('data/Sample_Game_1_RawEventsData.csv')

timestep = imported_home["Time [s]"].iloc[1] - imported_home["Time [s]"].iloc[0] # find timestep of imported data from csv

# pitch dimension in metres
PITCH_XDIM = 105
PITCH_YDIM = 68

frames_per_sample = 1 # how often will we sample the data - e.g. 5 = sample every 5 frames, 1 = keep every frame
sampled_timestep= frames_per_sample * timestep

tracking_home = imported_home.iloc[::frames_per_sample]
tracking_away = imported_away.iloc[::frames_per_sample]

tracking_home = Reformat(tracking_home) # reformat into more user friendly form
tracking_away = Reformat(tracking_away)

#change locs to actual vals in metres
tracking_home['x_loc'] = tracking_home['x_loc']*PITCH_XDIM
tracking_home['y_loc'] = tracking_home['y_loc']*PITCH_YDIM
tracking_away['x_loc'] = tracking_away['x_loc']*PITCH_XDIM
tracking_away['y_loc'] = tracking_away['y_loc']*PITCH_YDIM

imported_events[['start_x','end_x']] = imported_events[['start_x','end_x']]*PITCH_XDIM
imported_events[['start_y','end_y']] = imported_events[['start_y','end_y']]*PITCH_YDIM

#select just passes from events feed
passes = imported_events[imported_events['type']=='PASS']

#focus on home team passes
home_passes = passes[passes['team']=='Home']

#find the tracking frames associated with a pass receive event
home_receive_frames = list(home_passes['end_frame'])

#get the location of opposition players for said frames
home_receive_opplocs = tracking_away[tracking_away['frame'].isin(home_receive_frames)]

#convert this data back into wide format (pivot being opposite of melt) for this analysis as it is, for me, easier to visualise
hro_grouped = home_receive_opplocs.pivot(index='frame', columns='player', values=['x_loc', 'y_loc'])
hro_ball = hro_grouped[[('x_loc','Ball'),('y_loc','Ball')]]
hro_grouped = hro_grouped.drop([('x_loc','Ball'),('y_loc','Ball')], axis=1)

# create and fill dictionary with square of distance between location and ball for both x and y axis
xdiffs = {}
ydiffs = {}
for column in hro_grouped:
    xdiff2 = (hro_grouped[column]-hro_ball[('x_loc','Ball')])**2
    xdiffs[column] = xdiff2
    ydiff2 = (hro_grouped[column]-hro_ball[('y_loc','Ball')])**2
    ydiffs[column] = ydiff2
    
    
# convert to df and only keep valid distances   
xdiffs_df = pd.DataFrame(xdiffs)    
xdiffs_df = xdiffs_df.filter(like='x_loc')    
    
ydiffs_df = pd.DataFrame(ydiffs)    
ydiffs_df = ydiffs_df.filter(like='y_loc')

#find distance between player and ball for each pass receipt - can select min n, not just minimum as per next line
dists = np.sqrt(xdiffs_df.values + ydiffs_df.values)
min_dists = np.nanmin(dists,axis=1)

hro_ball['min_dist'] = min_dists

#get the half the pass was made as we will need to flip 2nd half for consistent view
hro_ball['period'] = home_passes['period'].values # .values otherwise it will look to match index

hro_ball.columns = ['x_loc','y_loc','dist','period']
hro_ball['x_loc'].loc[hro_ball['period'] == 2] = PITCH_XDIM - hro_ball['x_loc'] # flip 2nd half locs
hro_ball['y_loc'].loc[hro_ball['period'] == 2] = PITCH_YDIM - hro_ball['y_loc']  


#PLOTTING EXAMPLES - TODO: DEVELOP INTO REUSABLE FUNCTION(S)
##################################################################
# Plot pass receipt locations with nearest opponent distance

pitch = Pitch(pitch_color='#847596', line_color='white', figsize=(10, 8), pitch_type = 'metricasports',
              pitch_length=PITCH_XDIM, pitch_width=PITCH_YDIM)
fig, ax = pitch.draw()
sc = pitch.scatter(hro_ball['x_loc']/PITCH_XDIM, hro_ball['y_loc']/PITCH_YDIM, # mplsoccer plots coords in 0,1 range not actual metres
                   s=60, label='Pass Received', c = hro_ball['dist'], ax=ax, alpha = 0.8, cmap = matplotlib.cm.get_cmap('RdYlGn_r'),
                   vmin=0, vmax=15) # hard limit at 15 - don't want outliers compressing meaningful colour range

cb = fig.colorbar(sc, fraction = 0.02, pad = 0.01)
cb.set_label('Nearest Opponent (m)')
ax.set_title('Home Pass Receipt Locations', fontsize = 20)

##################################################################
# Plot pass receipt locations with min distance filter  

cutoff = 7.5
hro_ball_att = hro_ball[hro_ball['dist']>cutoff]
pitch = Pitch(pitch_color='#847596', line_color='white', figsize=(10, 8), pitch_type = 'metricasports',
              pitch_length=PITCH_XDIM, pitch_width=PITCH_YDIM)
fig, ax = pitch.draw()
sc = pitch.scatter(hro_ball_att['x_loc']/PITCH_XDIM, hro_ball_att['y_loc']/PITCH_YDIM,
                   s=60, label='Pass Received', c = hro_ball_att['dist'], ax=ax, alpha = 0.8,
                   cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", ["yellow","red"]),
                   vmin=8, vmax=15)

cb = fig.colorbar(sc, fraction = 0.02, pad = 0.01)
cb.set_label('Nearest Opponent (m)')
ax.set_title('Home Receipt Locations - In Space (min '+str(cutoff)+'m)', fontsize = 20)

##################################################################
# Plot complete frames for receipt locations of interest with distance to goal filter - attacking scernario

hro_ball_att['oppgoal_dist'] = np.sqrt((PITCH_XDIM - hro_ball_att['x_loc'])**2 + (hro_ball_att['y_loc']-(PITCH_YDIM/2))**2)

hro_ball_attfocus = hro_ball_att[hro_ball_att['oppgoal_dist']<=30] # 30m from goal

#get tracking data into dictionary of frames
attfocus_homedict = {}
attfocus_awaydict = {}
for ix in hro_ball_attfocus.index:
    homedata = tracking_home[tracking_home['frame']==ix]
    homedata['x_loc'].loc[homedata['period'] == 2] = PITCH_XDIM - homedata['x_loc'] # flip 2nd half locs
    homedata['y_loc'].loc[homedata['period'] == 2] = PITCH_YDIM - homedata['y_loc']
    attfocus_homedict[ix] = homedata
    
    awaydata = tracking_away[tracking_away['frame']==ix]
    awaydata['x_loc'].loc[awaydata['period'] == 2] = PITCH_XDIM - awaydata['x_loc'] # flip 2nd half locs
    awaydata['y_loc'].loc[awaydata['period'] == 2] = PITCH_YDIM - awaydata['y_loc']
    attfocus_awaydict[ix] = awaydata
    
# loop through frames and plot players on pitch   
for key in attfocus_homedict:
    #drop ball
    attfocus_homedict[key] = attfocus_homedict[key][attfocus_homedict[key].player != 'Ball']
    attfocus_awaydict[key] = attfocus_awaydict[key][attfocus_awaydict[key].player != 'Ball']
    
    pitch = Pitch(pitch_color='#847596', line_color='white', figsize=(10, 8), pitch_type = 'metricasports',
                  pitch_length=PITCH_XDIM, pitch_width=PITCH_YDIM)
    fig, ax = pitch.draw()
    sc1 = pitch.scatter(attfocus_homedict[key]['x_loc']/PITCH_XDIM, attfocus_homedict[key]['y_loc']/PITCH_YDIM,
                       s=150, label='Home', ax=ax, alpha = 0.8, c = 'yellow')
    sc2 = pitch.scatter(attfocus_awaydict[key]['x_loc']/PITCH_XDIM, attfocus_awaydict[key]['y_loc']/PITCH_YDIM,
                       s=150, label='Away', ax=ax, alpha = 0.8, c = 'red')
    
    ax.set_title('Player Locations: Frame '+str(key), fontsize = 14)
    
    start_loc = passes[passes['end_frame']==key]
    start_loc['start_x'].loc[start_loc['period'] == 2] = PITCH_XDIM - start_loc['start_x'] # flip 2nd half locs
    start_loc['start_y'].loc[start_loc['period'] == 2] = PITCH_YDIM - start_loc['start_y']
    
    #get origin of pass and plot as a comet on the pitch
    l1 = pitch.lines(start_loc['start_x']/PITCH_XDIM, start_loc['start_y']/PITCH_YDIM,
                     hro_ball_attfocus.loc[key,'x_loc']/PITCH_XDIM, hro_ball_attfocus.loc[key,'y_loc']/PITCH_YDIM, 
                     ax=ax, lw = 6, comet = True, color = 'yellow', label = 'Pass')
    
    ax.legend(edgecolor='None', fontsize=12, loc='upper left', handlelength=4)
    plt.suptitle('Attacking Passes Into Space', fontsize = 20)
    plt.show()

##################################################################
# Plot complete frames for receipt locations of interest with distance to goal filter - defensive scernario

hro_ball_def = hro_ball[hro_ball['dist']<2.5]
pitch = Pitch(pitch_color='#847596', line_color='white', figsize=(10, 8), pitch_type = 'metricasports',
              pitch_length=PITCH_XDIM, pitch_width=PITCH_YDIM)
fig, ax = pitch.draw()
sc = pitch.scatter(hro_ball_def['x_loc']/PITCH_XDIM, hro_ball_def['y_loc']/PITCH_YDIM,
                   s=60, label='Pass Received', c = hro_ball_def['dist'], ax=ax, alpha = 0.8,
                   cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", ["red","orange"]),
                   vmin=0, vmax=2.5)

cb = fig.colorbar(sc, fraction = 0.02, pad = 0.01)
cb.set_label('Nearest Opponent (m)')
ax.set_title('Home Receipt Locations - Closed Down', fontsize = 20)

hro_ball_def['owngoal_dist'] = np.sqrt((hro_ball_def['x_loc'])**2 + (hro_ball_def['y_loc']-(PITCH_YDIM/2))**2)

hro_ball_deffocus = hro_ball_def[hro_ball_def['owngoal_dist']<=30] # 30m from goal

deffocus_homedict = {}
deffocus_awaydict = {}
for ix in hro_ball_deffocus.index:
    homedata = tracking_home[tracking_home['frame']==ix]
    homedata['x_loc'].loc[homedata['period'] == 2] = PITCH_XDIM - homedata['x_loc'] # flip 2nd half locs
    homedata['y_loc'].loc[homedata['period'] == 2] = PITCH_YDIM - homedata['y_loc']
    deffocus_homedict[ix] = homedata
    
    awaydata = tracking_away[tracking_away['frame']==ix]
    awaydata['x_loc'].loc[awaydata['period'] == 2] = PITCH_XDIM - awaydata['x_loc'] # flip 2nd half locs
    awaydata['y_loc'].loc[awaydata['period'] == 2] = PITCH_YDIM - awaydata['y_loc']
    deffocus_awaydict[ix] = awaydata
    
#to go in loop to produce sub-pitches    
for key in deffocus_homedict:
    #drop ball
    deffocus_homedict[key] = deffocus_homedict[key][deffocus_homedict[key].player != 'Ball']
    deffocus_awaydict[key] = deffocus_awaydict[key][deffocus_awaydict[key].player != 'Ball']
    
    pitch = Pitch(pitch_color='#847596', line_color='white', figsize=(10, 8), pitch_type = 'metricasports',
                  pitch_length=PITCH_XDIM, pitch_width=PITCH_YDIM)
    fig, ax = pitch.draw()
    sc1 = pitch.scatter(deffocus_homedict[key]['x_loc']/PITCH_XDIM, deffocus_homedict[key]['y_loc']/PITCH_YDIM,
                       s=150, label='Home', ax=ax, alpha = 0.8, c = 'yellow')
    sc2 = pitch.scatter(deffocus_awaydict[key]['x_loc']/PITCH_XDIM, deffocus_awaydict[key]['y_loc']/PITCH_YDIM,
                       s=150, label='Away', ax=ax, alpha = 0.8, c = 'red')
    
    ax.set_title('Player Locations: Frame '+str(key), fontsize = 14)
    
    start_loc = passes[passes['end_frame']==key]
    start_loc['start_x'].loc[start_loc['period'] == 2] = PITCH_XDIM - start_loc['start_x'] # flip 2nd half locs
    start_loc['start_y'].loc[start_loc['period'] == 2] = PITCH_YDIM - start_loc['start_y']
    
    l1 = pitch.lines(start_loc['start_x']/PITCH_XDIM, start_loc['start_y']/PITCH_YDIM,
                     hro_ball_deffocus.loc[key,'x_loc']/PITCH_XDIM, hro_ball_deffocus.loc[key,'y_loc']/PITCH_YDIM, 
                     ax=ax, lw = 6, comet = True, color = 'yellow')
    plt.suptitle('High Risk Passes Into Pressure', fontsize = 20)
    plt.show()
    
##################################################################

# Focus on left wing receipts from attacking focus plot - where did they originate?  

#define area of interest
xmin = 0.66 * PITCH_XDIM # as perecentage of axis 
xmax = 1 * PITCH_XDIM

ymin = 0 * PITCH_YDIM
ymax = 0.25 *PITCH_YDIM  

#apply the location filter
hro_ball_areafocus  = hro_ball_att[(hro_ball_att['x_loc']>=xmin) & (hro_ball_att['x_loc']<=xmax) & (hro_ball_att['y_loc']>=ymin) & (hro_ball_att['y_loc']<=ymax)]  

hro_ball_areafocus = hro_ball_areafocus.merge(passes, left_index = True, right_on = 'end_frame')

hro_ball_areafocus['start_x'].loc[hro_ball_areafocus['period_x'] == 2] = PITCH_XDIM - hro_ball_areafocus['start_x'] # flip 2nd half locs
hro_ball_areafocus['start_y'].loc[hro_ball_areafocus['period_x'] == 2] = PITCH_YDIM - hro_ball_areafocus['start_y']

cols = ['start_x', 'start_y', 'x_loc', 'y_loc']
hro_ball_areafocus = hro_ball_areafocus[cols]

pitch = Pitch(pitch_color='#847596', line_color='white', figsize=(10, 8), pitch_type = 'metricasports',
                  pitch_length=PITCH_XDIM, pitch_width=PITCH_YDIM)
fig, ax = pitch.draw()

color = get_cmap('plasma')(np.linspace(0, 1, len(hro_ball_areafocus)))
sc1 = pitch.scatter(hro_ball_areafocus['x_loc']/PITCH_XDIM, hro_ball_areafocus['y_loc']/PITCH_YDIM,
                       s=100, label='Home', ax=ax, alpha = 0.8, c = color)
l1 = pitch.lines(hro_ball_areafocus['start_x']/PITCH_XDIM, hro_ball_areafocus['start_y']/PITCH_YDIM,
                     hro_ball_areafocus['x_loc']/PITCH_XDIM, hro_ball_areafocus['y_loc']/PITCH_YDIM, 
                     ax=ax, lw = 2, ls = 'dashed', color = color)
plt.suptitle('Home Passes to Left Wing - In Space (min '+str(cutoff)+'m)', fontsize = 20)


