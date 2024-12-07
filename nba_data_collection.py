import requests
import pandas as pd
from datetime import datetime

# Function to fetch player ID based on first and last name
def get_player_id(first_name, last_name):
    """
    Fetches the NBA player ID for a given player's name.

    Args:
        first_name (str): The player's first name.
        last_name (str): The player's last name.

    Returns:
        int: The player's NBA ID if found, otherwise None.
    """
    all_players = players.get_players()
    
    for player in all_players:
        if player['first_name'].lower() == first_name.lower() and player['last_name'].lower() == last_name.lower():
            return player['id']
    
    print(f"No player found with the name {first_name} {last_name}.")
    return None

# Function to fetch player position based on player ID
def get_player_position(player_id):
    """
    Fetches the NBA player's position from the API.

    Args:
        player_id (int): The player's NBA ID.

    Returns:
        str: The player's position.
    """
    url = f"https://www.balldontlie.io/api/v1/players/{player_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('position', 'Unknown')
    else:
        print(f"Failed to fetch position for player ID {player_id}. Status code: {response.status_code}")
        return 'Unknown'

# Function to fetch lines from Rotowire and append data to CSV
def fetch_lines():
    url = "https://www.rotowire.com/betting/nba/player-props.php"
    response = requests.get(url)

    soup = BeautifulSoup(response.content, 'html.parser')

    stats = ["PTS", "REB", "AST", "THREES"]
    all_lines = {}

    for stat in stats:
        table = soup.find('div', class_='prop-table', attrs={'data-prop': stat})

        data = {}
        if table:
            data_prop = table.get('data-prop')

            if table.script:
                raw_javascript = [line.strip() for line in table.script.text.splitlines() if line.strip().startswith('data')]
                if raw_javascript:
                    json_string = raw_javascript[0][6:-1]
                    data[data_prop] = json.loads(json_string)

        if data:
            combined_data = []
            for key, value in data.items():
                combined_data.extend(value)
            df = pd.DataFrame(combined_data)
            headers = ['name', 'team', 'opp', f'fanduel_{stat.lower()}', f'fanduel_{stat.lower()}Under', f'fanduel_{stat.lower()}Over']
            df = df[headers]
            df = df.dropna()
            
            # Add Date column
            today_date = datetime.today().strftime('%Y-%m-%d')
            df.insert(0, 'Date', today_date)

            # Add H/A column
            ha_status = []
            for i in range(len(df)):
                if '@' in df.iloc[i, 2]:
                    df.iloc[i, 2] = df.iloc[i, 2].strip('@')
                    ha_status.append('@')
                else:
                    ha_status.append('vs')
            df.insert(df.columns.get_loc('opp'), 'H/A', ha_status)

            # Add Player Positions column by fetching the player ID and position
            positions = []
            for i, row in df.iterrows():
                first_name, last_name = row['name'].split()  # Assuming name is in 'First Last' format
                player_id = get_player_id(first_name, last_name)
                if player_id:
                    position = get_player_position(player_id)
                else:
                    position = 'Unknown'
                positions.append(position)
            df.insert(1, 'Position', positions)  # Insert the Position column into the second column

            df.rename(columns={f'fanduel_{stat.lower()}': f'fanduel_{stat.lower()}_line'}, inplace=True)
            df.columns = df.columns.str.upper()

            # Add DataFrame to all_data dictionary
            all_lines[stat] = df

    return all_lines


# Function to append to CSV
def append_to_csv(df, filename):
    if not df.empty:
        # Check if today's date is already in the file
        try:
            existing_df = pd.read_csv(filename)
            if today_date in existing_df['Date'].values:
                print(f"Data for {today_date} already exists in the CSV. Not appending.")
            else:
                df.to_csv(filename, mode='a', header=False, index=False)
                print(f"Appended data for {today_date} to {filename}.")
        except FileNotFoundError:
            # If the file doesn't exist, create it and add the DataFrame
            df.to_csv(filename, mode='w', header=True, index=False)
            print(f"Created new CSV file: {filename}")
    else:
        print("DataFrame is empty, not appending.")

def main():
    # Fetch the player prop lines
    all_lines = fetch_lines()

    # Iterate over each stat DataFrame and append to CSV
    for stat, df in all_lines.items():
        append_to_csv(df, f"nba_player_props_{stat}.csv")

if __name__ == "__main__":
    main()
