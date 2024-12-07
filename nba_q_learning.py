import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
import os
from datetime import datetime
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
import re

def fetch_lines():
    lineups = get_lineups()
    abbr_to_team_name = {
                        "ATL": "Hawks", "BOS": "Celtics", "BKN": "Nets", "CHA": "Hornets", "CHI": "Bulls",
                        "CLE": "Cavaliers", "DAL": "Mavericks", "DEN": "Nuggets", "DET": "Pistons", "GSW": "Warriors",
                        "HOU": "Rockets", "IND": "Pacers", "LAC": "Clippers", "LAL": "Lakers", "MEM": "Grizzlies",
                        "MIA": "Heat", "MIL": "Bucks", "MIN": "Timberwolves", "NOP": "Pelicans", "NYK": "Knicks",
                        "OKC": "Thunder", "ORL": "Magic", "PHI": "76ers", "PHX": "Suns", "POR": "Blazers",
                        "SAC": "Kings", "SAS": "Spurs", "TOR": "Raptors", "UTA": "Jazz", "WAS": "Wizards"
                    }
        
    # Your target URL
    url = "https://www.rotowire.com/betting/nba/player-props.php"
    
    try:
        # Send HTTP request and check if the request was successful
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return {}

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # List of stats to be extracted
    stats = ["PTS", "REB", "AST", "THREES"]

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
            headers = ['name', 'team', 'opp', f'fanduel_{stat.lower()}', f'fanduel_{stat.lower()}Under', f'fanduel_{stat.lower()}Over']
            df = df[headers]
            df = df.dropna()

            ha_status = []
            for i in range(len(df)):
                if '@' in df.iloc[i, 2]:
                    df.iloc[i, 2] = df.iloc[i, 2].strip('@')
                    ha_status.append('@')
                else:
                    ha_status.append('vs')
            df.insert(df.columns.get_loc('opp'), 'H/A', ha_status)

            df.rename(columns={f'fanduel_{stat.lower()}': f'fanduel_{stat.lower()}_line'}, inplace=True)
            df.columns = df.columns.str.upper()

            # Add Date column with today's date as the first column
            today_date = datetime.today().strftime('%Y-%m-%d')
            df.insert(0, 'DATE', today_date)
            player_pos = []
            for i in range(len(df)):
                team_abbr = df.iloc[i,2]
                opp_abbr = df.iloc[i,4]
                df.iloc[i,2] = abbr_to_team_name.get(team_abbr)
                df.iloc[i,4] = abbr_to_team_name.get(opp_abbr)
                team = df.iloc[i,2]
                player = df.iloc[i,1]
                starters = lineups[team]
                
                if player.upper() == starters[0].upper() or player.upper() == starters[1].upper():
                    print(f'{player} is a guard')
                    player_pos.append('G')
                elif player.upper() == starters[2].upper() or player.upper() == starters[3].upper():
                    print(f'{player} is a forward')
                    player_pos.append('F')
                elif player.upper() == starters[4].upper():
                    print(f'{player} is a center')
                    player_pos.append('C')
                else:
                    player_pos.append('None')
            df.insert(1,'POS',player_pos)
            df.drop(df[df.isin(["None"]).any(axis=1)].index, inplace=True)
            
            # Add DataFrame to all_lines dictionary
            all_lines[stat] = df
        else:
            print(f"No data found for stat: {stat}")

    return all_lines

def get_lineups():
    '''Fetch NBA matchups and lineups from Rotowire and associate them with the correct teams.'''

    url_teams_lineups = "https://www.rotowire.com/basketball/nba-lineups.php"
    response = requests.get(url_teams_lineups)
    soup = BeautifulSoup(response.content, 'html.parser')

    lineups_data = {}

    # Get all lineup boxes
    lineups = soup.find_all('div', class_='lineup__box')

    for lineup in lineups:
        # Get the matchup text
        matchup = lineup.find('div', class_='lineup__matchup')
        

        if matchup:
            matchup_text = matchup.get_text(strip=True)
            teams = re.findall(r'\b[A-Za-z0-9]+\b(?=\()', matchup_text)
            # Initialize dictionary for teams in this matchup
            for team in teams:
                lineups_data[team] = {}
                # Now, we need to extract the player names for both teams
                if team == teams[0]:
                    team_type = "is-visit"
                elif team == teams[1]:
                    team_type = "is-home"
                lineup_list = lineup.find('ul', class_=f'lineup__list {team_type}')
                if lineup_list:
                    players = lineup_list.find_all('li', class_='lineup__player')
                    team_players = []
                    for player in players:
                        name_tag = player.find('a')
                        if name_tag:
                            name = name_tag.get('title', name_tag.get_text(strip=True))
                            team_players.append(name)
                    lineups_data[team] = team_players[:5]
        else:
            print(f"Warning: No Matchup Found For {teams}")   
                    
                
    return lineups_data



              

def main():
    

    try:
        all_lines = fetch_lines()

        if not all_lines:
            print("No data fetched. Exiting.")
            return

        today_date = datetime.today().strftime('%Y-%m-%d')  # Define today's date here

        output_folder = "nba_player_props"
        os.makedirs(output_folder, exist_ok=True)

        for stat, df in all_lines.items():
            file_path = os.path.join(output_folder, f"{stat.lower()}.csv")
            
            # Check if today's date is already in the CSV file
            if os.path.exists(file_path):
                existing_data = pd.read_csv(file_path)
                if today_date in existing_data['DATE'].values:
                    print(f"Data for {stat} with today's date ({today_date}) already exists. Skipping append.")
                    continue

            # Append data to the CSV file
            df.to_csv(file_path, mode='a', index=False, header=not os.path.exists(file_path))
            print(f"Data for {stat} appended to {file_path}")


    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
