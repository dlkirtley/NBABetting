import requests
from bs4 import BeautifulSoup
import re

def get_lineups():
    '''Fetch NBA matchups and lineups from Rotowire and associate them with the correct teams.'''
    abbr_to_team_name = {
        "ATL": "Atlanta", "BOS": "Boston", "BKN": "Brooklyn", "CHA": "Charlotte", "CHI": "Chicago",
        "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver", "DET": "Detroit", "GSW": "Golden State",
        "HOU": "Houston", "IND": "Indiana", "LAC": "LA Clippers", "LAL": "LA Lakers", "MEM": "Memphis",
        "MIA": "Miami", "MIL": "Milwaukee", "MIN": "Minnesota", "NOP": "New Orleans", "NYK": "New York",
        "OKC": "Okla City", "ORL": "Orlando", "PHI": "Philadelphia", "PHX": "Phoenix", "POR": "Portland",
        "SAC": "Sacramento", "SAS": "San Antonio", "TOR": "Toronto", "UTA": "Utah", "WAS": "Washington"
    }

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
                    print(team, lineups_data[team])   
        else:
            print(f"Warning: No Matchup Found For {teams}")   
                    
                
    return lineups_data


def main():
    lineups = get_lineups()
    print(lineups)
    


if __name__ == "__main__":
    main()
