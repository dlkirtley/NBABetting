from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
import pandas as pd

def get_player_id(player_name):
    """
    Fetch the player ID for a given player name using nba_api.
    
    Parameters:
        player_name (str): Full name of the player (e.g., "LeBron James").
    
    Returns:
        int: The player's ID if found, otherwise None.
    """
    player_dict = players.get_players()
    for player in player_dict:
        if player['full_name'].lower() == player_name.lower():
            return player['id']
    print(f"Player '{player_name}' not found.")
    return None

def get_player_game_log(player_id, season='2023-24', season_type='Regular Season'):
    """
    Fetch the game log for a player using their ID.
    
    Parameters:
        player_id (int): The player's ID.
        season (str): The NBA season in 'YYYY-YY' format.
        season_type (str): Either 'Regular Season' or 'Playoffs'.
    
    Returns:
        pd.DataFrame: The player's game log as a DataFrame.
    """
    game_log = playergamelog.PlayerGameLog(player_id=player_id, season=season, season_type_all_star=season_type)
    game_log_data = game_log.get_data_frames()
    
    if game_log_data:
        return game_log_data[0]  # The first DataFrame contains the game log
    print(f"No game log data found for player ID {player_id} in the {season} season.")
    return pd.DataFrame()

def main():
    player_name = input("Enter the player's full name: ")
    
    # Step 1: Get the player's ID
    player_id = get_player_id(player_name)
    if player_id is None:
        return
    
    # Step 2: Get the player's game log
    season = input("Enter the season (e.g., '2023-24'): ")
    season_type = input("Enter the season type ('Regular Season' or 'Playoffs'): ")
    
    game_log_df = get_player_game_log(player_id, season=season, season_type=season_type)
    
    # Step 3: Display or save the game log
    if not game_log_df.empty:
        print("\nGame Log:")
        print(game_log_df.head())  # Display the first few rows
        # Save to CSV if needed
        game_log_df.to_csv(f"{player_name.replace(' ', '_')}_game_log_{season}.csv", index=False)
        print(f"Game log saved as '{player_name.replace(' ', '_')}_game_log_{season}.csv'")
    else:
        print("No game log available.")

if __name__ == "__main__":
    main()
