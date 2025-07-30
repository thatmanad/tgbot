"""
Goated.com API client for fetching affiliate data.
"""

import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from config.settings import get_settings

logger = logging.getLogger(__name__)

class GoatedAPI:
    """Client for interacting with goated.com API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.GOATED_API_URL
        self.api_key = self.settings.GOATED_API_KEY
        self.session = None
        
        # Rate limiting
        self.last_request_time = {}
        self.request_count = {}
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            headers = {
                'User-Agent': 'GoatedWagerBot/1.0',
                'Content-Type': 'application/json'
            }
            
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
                # or headers['X-API-Key'] = self.api_key depending on their auth method
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        
        return self.session
    
    async def _rate_limit_check(self, endpoint: str) -> None:
        """Check rate limiting before making request."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old requests
        if endpoint in self.request_count:
            self.request_count[endpoint] = [
                req_time for req_time in self.request_count[endpoint] 
                if req_time > minute_ago
            ]
        else:
            self.request_count[endpoint] = []
        
        # Check if we're over the limit
        if len(self.request_count[endpoint]) >= self.settings.MAX_REQUESTS_PER_MINUTE:
            sleep_time = 60 - (now - self.request_count[endpoint][0]).seconds
            logger.warning(f"Rate limit reached for {endpoint}, sleeping for {sleep_time}s")
            await asyncio.sleep(sleep_time)
        
        # Record this request
        self.request_count[endpoint].append(now)
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make HTTP request to the API."""
        await self._rate_limit_check(endpoint)
        
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            logger.info(f"Making request to {url}")
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"API response: {data}")
                    return data
                elif response.status == 401:
                    logger.error("API authentication failed")
                    return None
                elif response.status == 404:
                    logger.warning(f"API endpoint not found: {url}")
                    return None
                else:
                    logger.error(f"API request failed with status {response.status}")
                    return None
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error making API request: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error making API request: {e}")
            return None
    
    async def find_player_by_username(self, username: str, affiliate_ids: list = None) -> Optional[Dict[str, Any]]:
        """Find a player by username across affiliate networks."""
        try:
            # Default list of affiliate IDs to search through
            # You can expand this list with known affiliate IDs
            if affiliate_ids is None:
                affiliate_ids = ["UCW47GH", "AFFILIATE2", "AFFILIATE3"]  # Add more affiliate IDs as needed

            for affiliate_id in affiliate_ids:
                endpoint = f"user/affiliate/referral-leaderboard/{affiliate_id}"
                response = await self._make_request(endpoint)

                if response and response.get('success'):
                    players = response.get('data', [])

                    # Search for the player by username (case-insensitive)
                    for player in players:
                        if player.get('name', '').lower() == username.lower():
                            # Found the player! Return their data with affiliate info
                            return {
                                'uid': player.get('uid'),
                                'name': player.get('name'),
                                'wagered': player.get('wagered', {}),
                                'affiliate_id': affiliate_id,
                                'found': True
                            }

            # Player not found in any affiliate network
            return None

        except Exception as e:
            logger.error(f"Error finding player {username}: {e}")
            return None

    async def validate_username(self, username: str) -> bool:
        """Validate if a username exists in the system."""
        try:
            player_data = await self.find_player_by_username(username)
            return player_data is not None

        except Exception as e:
            logger.error(f"Error validating username {username}: {e}")
            return False
    
    async def get_player_wager_stats(self, username: str) -> Optional[Dict[str, Any]]:
        """Get wager statistics for a specific player."""
        try:
            # Find the player first
            player_data = await self.find_player_by_username(username)

            if not player_data:
                return None

            wagered = player_data.get('wagered', {})
            daily_wager = wagered.get('today', 0)
            total_wager = wagered.get('all_time', 0)

            # Record today's wager for rolling 7-day calculation
            from database.connection import record_daily_wager, calculate_rolling_7_day_wager
            await record_daily_wager(player_data.get('name'), daily_wager, total_wager)

            # Calculate true rolling 7-day wager
            rolling_7_day_wager = await calculate_rolling_7_day_wager(player_data.get('name'))

            return {
                'username': player_data.get('name'),
                'uid': player_data.get('uid'),
                'daily_wager': daily_wager,
                'weekly_wager': wagered.get('this_week', 0),
                'last_7_days_wager': rolling_7_day_wager,  # True rolling 7-day calculation
                'monthly_wager': wagered.get('this_month', 0),
                'total_wager': total_wager,
                'affiliate_id': player_data.get('affiliate_id'),
                'last_updated': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching wager stats for player {username}: {e}")
            return None
    
    async def get_player_leaderboard_position(self, username: str) -> Optional[Dict[str, Any]]:
        """Get leaderboard position for a specific player within their affiliate network."""
        try:
            # Find the player first
            player_data = await self.find_player_by_username(username)

            if not player_data:
                return None

            affiliate_id = player_data.get('affiliate_id')
            player_wagered = player_data.get('wagered', {})

            # Get all players in the same affiliate network
            endpoint = f"user/affiliate/referral-leaderboard/{affiliate_id}"
            response = await self._make_request(endpoint)

            if response and response.get('success'):
                all_players = response.get('data', [])

                # Calculate player's rank for each time period
                def get_rank(time_period):
                    # Sort players by wager amount for this time period (descending)
                    sorted_players = sorted(
                        all_players,
                        key=lambda x: x.get('wagered', {}).get(time_period, 0),
                        reverse=True
                    )

                    # Find player's position (1-based)
                    for i, player in enumerate(sorted_players):
                        if player.get('name', '').lower() == username.lower():
                            return i + 1
                    return None

                daily_rank = get_rank('today')
                weekly_rank = get_rank('this_week')
                # For now, use weekly rank as last 7 days rank since we can't calculate rolling 7-day for all players
                last_7_days_rank = get_rank('this_week')
                monthly_rank = get_rank('this_month')
                all_time_rank = get_rank('all_time')

                # Get network totals
                network_total_today = sum(p.get('wagered', {}).get('today', 0) for p in all_players)
                network_total_week = sum(p.get('wagered', {}).get('this_week', 0) for p in all_players)
                network_total_month = sum(p.get('wagered', {}).get('this_month', 0) for p in all_players)
                network_total_all_time = sum(p.get('wagered', {}).get('all_time', 0) for p in all_players)

                # Get the player's rolling 7-day wager
                from database.connection import calculate_rolling_7_day_wager
                player_rolling_7_days = await calculate_rolling_7_day_wager(player_data.get('name'))

                return {
                    'username': player_data.get('name'),
                    'uid': player_data.get('uid'),
                    'affiliate_id': affiliate_id,
                    'daily_rank': daily_rank,
                    'weekly_rank': weekly_rank,
                    'last_7_days_rank': last_7_days_rank,
                    'monthly_rank': monthly_rank,
                    'all_time_rank': all_time_rank,
                    'total_players': len(all_players),
                    'player_daily': player_wagered.get('today', 0),
                    'player_weekly': player_wagered.get('this_week', 0),
                    'player_last_7_days': player_rolling_7_days,  # True rolling 7-day calculation
                    'player_monthly': player_wagered.get('this_month', 0),
                    'player_all_time': player_wagered.get('all_time', 0),
                    'network_daily': network_total_today,
                    'network_weekly': network_total_week,
                    'network_monthly': network_total_month,
                    'network_all_time': network_total_all_time,
                    'last_updated': datetime.now().isoformat()
                }

            return None

        except Exception as e:
            logger.error(f"Error fetching leaderboard position for player {username}: {e}")
            return None
    
    async def get_full_leaderboard(self, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get the full leaderboard (optional feature)."""
        try:
            endpoint = "leaderboard"
            params = {'limit': limit}
            response = await self._make_request(endpoint, params)

            if response:
                return response

            return None

        except Exception as e:
            logger.error(f"Error fetching full leaderboard: {e}")
            return None

    async def get_top_leaderboard_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top players from all affiliate networks for weekly snapshot."""
        try:
            # Get affiliate IDs from registered users
            from database.connection import get_all_active_users

            users = await get_all_active_users()
            affiliate_ids = set()

            # Find affiliate networks by checking where our users are registered
            for user in users:
                username = user.get('goated_username', '')
                if username:
                    try:
                        player_data = await self.find_player_by_username(username)
                        if player_data and player_data.get('affiliate_id'):
                            affiliate_ids.add(player_data['affiliate_id'])
                    except Exception as e:
                        logger.warning(f"Error finding affiliate for user {username}: {e}")

            # Convert to list and add some common ones as fallback
            affiliate_ids = list(affiliate_ids)
            if not affiliate_ids:
                # Fallback to common affiliate IDs if none found
                affiliate_ids = ["UCW47GH", "GOATED", "GOATED2", "GOATED3"]

            logger.info(f"Checking affiliate networks: {affiliate_ids}")

            all_players = []

            # Fetch players from each affiliate network
            for affiliate_id in affiliate_ids:
                try:
                    endpoint = f"user/affiliate/referral-leaderboard/{affiliate_id}"
                    response = await self._make_request(endpoint)

                    if response and response.get('success'):
                        players = response.get('data', [])

                        # Add affiliate_id to each player and extract relevant data
                        for player in players:
                            wagered = player.get('wagered', {})
                            player_data = {
                                'username': player.get('name', ''),
                                'affiliate_id': affiliate_id,
                                'daily_wager': wagered.get('daily', 0),
                                'weekly_wager': wagered.get('weekly', 0),
                                'last_7_days_wager': wagered.get('last_7_days', wagered.get('weekly', 0)),
                                'monthly_wager': wagered.get('monthly', 0),
                                'all_time_wager': wagered.get('all_time', 0),
                                'total_players': len(players)
                            }
                            all_players.append(player_data)

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.warning(f"Error fetching leaderboard for affiliate {affiliate_id}: {e}")
                    continue

            # Sort by weekly wager (or last_7_days_wager) descending and return top players
            all_players.sort(key=lambda x: x.get('last_7_days_wager', x.get('weekly_wager', 0)), reverse=True)

            # Filter out players with 0 weekly wager for better results
            top_players = [p for p in all_players if p.get('last_7_days_wager', p.get('weekly_wager', 0)) > 0]

            # If we don't have enough players with wagers, include some with 0 wagers
            if len(top_players) < limit:
                zero_wager_players = [p for p in all_players if p.get('last_7_days_wager', p.get('weekly_wager', 0)) == 0]
                top_players.extend(zero_wager_players[:limit - len(top_players)])

            result = top_players[:limit]

            logger.info(f"Fetched {len(all_players)} total players, returning top {len(result)} by weekly wager")
            if result:
                top_wager = result[0].get('last_7_days_wager', result[0].get('weekly_wager', 0))
                logger.info(f"Top player weekly wager: ${top_wager:,.2f}")

            return result

        except Exception as e:
            logger.error(f"Error fetching top leaderboard players: {e}")
            return []
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

# Example usage and testing functions
async def test_api():
    """Test function for API connectivity."""
    async with GoatedAPI() as api:
        # Test validation
        is_valid = await api.validate_affiliate_id("test123")
        print(f"Validation test: {is_valid}")
        
        # Test wager stats
        wager_stats = await api.get_wager_stats("test123")
        print(f"Wager stats: {wager_stats}")
        
        # Test leaderboard
        leaderboard = await api.get_leaderboard_position("test123")
        print(f"Leaderboard position: {leaderboard}")

if __name__ == "__main__":
    # Run test if this file is executed directly
    asyncio.run(test_api())
