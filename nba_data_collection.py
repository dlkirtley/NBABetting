import requests
from bs4 import BeautifulSoup
import pandas as pd
from pdb import set_trace
import os
import dataclasses
import json
from datetime import datetime
import pytz
import re
import numpy as np
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
import tensorflow as tf

def find_game_data():
    print('Loading Schedule...')
    url_teams_lineups = "https://www.rotowire.com/basketball/nba-lineups.php"
    response = requests.get(url_teams_lineups)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Get all lineup boxes
    lineups = soup.find_all('div', class_='lineup__box')
    return lineups

def find_matchups(lineups):
    matches = []
    active_teams = []
    for lineup in lineups:
        # Get the matchup text
        matchup = lineup.find('div', class_='lineup__matchup')
        if matchup:
            matchup_text = matchup.get_text(strip=True)
            teams = re.findall(r'\b[A-Za-z0-9]+\b(?=\()', matchup_text)
            matches.append(teams)
            if len(teams) == 2:
                active_teams.append(teams[0])
                active_teams.append(teams[1])
    return active_teams, matches

def find_d_stats(positions,headers):
    print('Loading Weak Defenses...')
    url_defense = "https://www.fantasypros.com/daily-fantasy/nba/fanduel-defense-vs-position.php"
    response = requests.get(url_defense)
    soup = BeautifulSoup(response.content, 'html.parser')

    position_dataframes = {}  # Dictionary to hold DataFrame for each position

    for pos in positions:
        all_data = []  # List to hold each row of data for the current position

        # Find all rows with the specific class for each position
        rows = soup.find_all('tr', class_=f"GC-0 {pos}")

        for row in rows:
            # Get all `td` elements in the row
            cells = row.find_all('td')
            row_data = [cell.get_text(strip=True) for cell in cells]  # Extract text from each cell
            all_data.append(row_data)  # Append the row data to all_data
            row_data[0] = row_data[0].split()[-1]
        # Convert the data to a DataFrame and store it in the dictionary
        position_dataframes[pos] = pd.DataFrame(all_data, columns = headers)

    return position_dataframes

def sort_bad_d(positions,headers,stats,active_teams,d_stats,m):
    pos_list = []
    stat_list = []
    defense_list = []
    for pos in positions:
        data = d_stats[f'{pos}']
        data.iloc[:,1:] = data.iloc[:,1:].apply(pd.to_numeric, errors='coerce')
        for stat in stats:
            idx = headers.index(stat)
            data.sort_values(by=data.columns[idx], inplace=True, ascending=False)
            for i in range(m):
                if data.iloc[i,0] in active_teams:
                    pos_list.append(pos)
                    stat_list.append(stat)
                    defense_list.append(data.iloc[i,0])
    boi = list(zip(pos_list,stat_list,defense_list))
    boi3 = pd.DataFrame(boi, columns = ["POS","STAT","DEFENSE"]) #BOI - Bets of Interest
    ha_status = []
    for defense in boi3.iloc[:,2]:
        index = active_teams.index(defense)
        if index%2 == 0:
            ha_status.append('@')
        elif index%2 == 1:
            ha_status.append('vs')
    boi3['HA STATUS'] = ha_status
    return boi3

def fill_opps(boi3,matches):
    opp_list = []
    for i in range(len(boi3)):
        for match in matches:
            if boi3.iloc[i,2] in match:
                if boi3.iloc[i,2] == match[0]:
                    opp_list.append(match[1])
                    break
                elif boi3.iloc[i,2] == match[1]:
                    opp_list.append(match[0])
                    break

    boi3["OPP"] = opp_list
    boi4 = boi3
    return boi4

def fill_players(boi4,lineups):
    print('Loading Opposing Players...')
    opp_player_list = []
    for i in range(len(boi4)):
        team_players = []
        opp_team = boi4.iloc[i,4]



        for lineup in lineups:
            # Get the matchup text
            matchup = lineup.find('div', class_='lineup__matchup')

            if matchup:
                matchup_text = matchup.get_text(strip=True)
                teams = re.findall(r'\b[A-Za-z0-9]+\b(?=\()', matchup_text)
                if opp_team in teams:
                    team_ind = teams.index(f'{opp_team}')
                    if team_ind == 0:
                        team_type = "is-visit"
                    elif team_ind ==1:
                        team_type = "is-home"
                    # Search both visiting and home team lists
                    break
            else:
                print("No Matchup")
        lineup_list = lineup.find('ul', class_=f'lineup__list {team_type}')

        if lineup_list:
            players = lineup_list.find_all('li', class_='lineup__player')

            # Extract only player names
            for player in players:
                name_tag = player.find('a')
                if name_tag:
                    name = name_tag.get('title',name_tag.get_text(strip=True))
                    team_players.append(name)
        if boi4.iloc[i,0] == "PG":
            opp_player_list.append(team_players[0])
        elif boi4.iloc[i,0] == "SG":
            opp_player_list.append(team_players[1])
        elif boi4.iloc[i,0] == "SF":
            opp_player_list.append(team_players[2])
        elif boi4.iloc[i,0] == "PF":
            opp_player_list.append(team_players[3])
        elif boi4.iloc[i,0] == "C":
            opp_player_list.append(team_players[4])
    boi4["OPP PLAYER"] = opp_player_list
    boi5 = boi4
    return boi5

def get_player_avg(boi5,n):
    headers = ["Name","Date","TEAM"," ","OPP","MIN","PTS","REB","AST","STL","BLK","FGM","FGA","FG%","3PM","3PA","3P%","FTM","FTA","FT%","TS%","OREB","DREB","TOV","PF","+/-"]
    stats = []
    player_stats = {}
    for i in range(len(boi5)):
        all_data = []
        player = boi5.iloc[i,5]
        player = re.sub(r'[éèêë]', 'e', player)
        player = re.sub(r'[áàâäã]', 'a', player)
        player = re.sub(r'[íìîï]', 'i', player)
        player = re.sub(r'[óòôöõ]', 'o', player)
        player = re.sub(r'[úùûü]', 'u', player)
        player = re.sub(r'[ç]', 'c', player)
        player_names = player.split()
        stat = boi5.iloc[i,1]
        print(f'Loading {stat} Data for {player}...')
        if len(player_names) == 2:
            player_url = f"https://www.statmuse.com/nba/ask/{player_names[0].lower()}-{player_names[1].lower()}-last-{n}-games"
        elif len(player_names) == 3:
            player_url = f"https://www.statmuse.com/nba/ask/{player_names[0].lower()}-{player_names[1].lower()}-{player_names[2].lower()}-last-{n}-games"
        else:
            print(player, 'is an unknown format')

        response = requests.get(player_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        rows = soup.find_all('tr')
        n_rows = rows[1:n+3]
        for row in n_rows:
            cells = row.find_all('td')
            row_data = [cell.get_text(strip=True) for cell in cells]
            all_data.append(row_data)
        if len(all_data) == n+2:
            player_df = pd.DataFrame(all_data)
            player_df = player_df.iloc[:,2:]
            for j in range(n):
                player_df.iloc[j,0] = player
            player_df.columns = headers
            player_stats[player] = player_df

        else:
            print("Not Enough Player Data")

    return player_stats

def fill_stats(boi5,player_stats,n):
    stat_avg_list = []
    stat_med_list = []
    for i in range(len(boi5)):
        player = boi5.iloc[i,5]
        stat = boi5.iloc[i,1]
        df = player_stats[player]
        df.replace("None",np.nan, inplace=True)
        df.dropna(inplace=True)
        # Iterate through columns 6, 7, and 8
        columns_to_convert = [6, 7, 8]

        for col in columns_to_convert:
            # Convert the column to numeric, handling non-numeric values
            df.iloc[:, col] = pd.to_numeric(df.iloc[:, col], errors='coerce')

        z = len(df)-2
        if stat == "PTS":
            fill_stat = df.iloc[z,6]
            med_stat = np.median(df.iloc[:z-1,6])
        elif stat == "REB":
            fill_stat = df.iloc[z,7]
            med_stat = np.median(df.iloc[:z-1,7])
        elif stat == "AST":
            fill_stat = df.iloc[z,8]
            med_stat = np.median(df.iloc[:z-1,8])
        stat_avg_list.append(fill_stat)
        stat_med_list.append(med_stat)

    boi5[f"L{n} AVG"] = stat_avg_list
    boi5[f"L{n} MED"] = stat_med_list
    boi6 = boi5
    return boi6



def fetch_lines():
    # Your target URL
    url = "https://www.rotowire.com/betting/nba/player-props.php"
    response = requests.get(url)

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # List of stats to be extracted
    stats = ["PTS", "REB", "AST"]

    all_lines = {}

    for stat in stats:
        # Find the div with the given class and data-prop attribute matching the input stat
        table = soup.find('div', class_='prop-table', attrs={'data-prop': stat})

        # Initialize an empty dictionary to store the data
        data = {}

        if table:
            # Get the data-prop attribute for the current prop_table
            data_prop = table.get('data-prop')

            # Ensure that the script tag exists
            if table.script:
                # Extract the data from the script tag
                raw_javascript = [
                    line.strip()
                    for line in table.script.text.splitlines()
                    if line.strip().startswith('data')
                ]

                if raw_javascript:
                    # [0]: there's only one line starting with "data" per script
                    # [6:-1]: remove the "data: " part and the trailing comma
                    json_string = raw_javascript[0][6:-1]

                    # Add the data to the dictionary using the data-prop attribute
                    data[data_prop] = json.loads(json_string)

        # Convert the collected data to a pandas DataFrame
        if data:
            combined_data = []
            for key, value in data.items():
                combined_data.extend(value)

            df = pd.DataFrame(combined_data)
            headers = ['name', f'fanduel_{stat.lower()}', f'fanduel_{stat.lower()}Under', f'fanduel_{stat.lower()}Over']
            df = df[headers]

            # Add DataFrame to all_data dictionary
            all_lines[stat] = df

            # Display the DataFrame
            #print(f"Data for {stat}:")
            #print(df)
        else:
            print(f"No data found for stat: {stat}")

    return all_lines

def fill_lines(boi6, all_lines):
    lines = []
    underodds = []
    overodds = []

    for i in range(len(boi6)):
        player = boi6.iloc[i, 5]
        stat = boi6.iloc[i, 1]
        df = all_lines[stat]

        # Find the row in df where the player is found
        player_row = df[df['name'] == player]

        if not player_row.empty:
            lines.append(player_row.iloc[0, 1])  # fanduel_{stat.lower()}
            underodds.append(player_row.iloc[0, 2])  # fanduel_{stat.lower()}Under
            overodds.append(player_row.iloc[0, 3])  # fanduel_{stat.lower()}Over
        else:
            # Handle the case where the player is not found
            lines.append(None)
            underodds.append(None)
            overodds.append(None)

    print(len(boi6))
    print(len(lines))

    boi7 = boi6.copy()
    boi7['STAT LINE'] = lines
    boi7['UNDER ODDS'] = underodds
    boi7['OVER ODDS'] = overodds

    return boi7







def main():
    n = 10
    m = 3
    positions = ["PG", "SG","SF","PF","C"]
    stats =  ["PTS","REB","AST"]
    headers = ["TEAM","GP","PTS","REB","AST","3PM","STL","BLK","TO","FD PTS"]
    lineups = find_game_data()

    active_teams, matches= find_matchups(lineups)
    d_stats = find_d_stats(positions,headers)
    boi3 = sort_bad_d(positions,headers,stats,active_teams,d_stats,m)
    boi4 = fill_opps(boi3,matches)
    boi5 = fill_players(boi4,lineups)
    print(boi5)


    player_stats = get_player_avg(boi5,n)
    boi6 = fill_stats(boi5,player_stats,n)
    print(boi6)
    all_lines = fetch_lines()

    boi7 = fill_lines(boi6, all_lines)
    boi7 = boi7.dropna()

    boi8 = boi7
    line_diff = []
    for i in range(len(boi7)):
        line_diff.append(float(boi7.iloc[i,8])-float(boi7.iloc[i,6]))

    boi8['LINE DIFF'] = line_diff
    boi8 = boi8.sort_values(by="LINE DIFF",ascending=True)
    print(boi8)


    csv_file = "NBA Bets.csv"
    boi8.to_csv(csv_file,index = False)
   # os.startfile(csv_file)



if __name__ == "__main__":
    main()