"""Fetch token metadata directly from Solana blockchain + IPFS"""
import httpx
from typing import Optional, Dict
from solders.pubkey import Pubkey
from solana.rpc.api import Client


class MetadataFetcher:
    """Fetches token metadata from Solana blockchain and IPFS"""

    def __init__(self, rpc_url: str = None):
        # Use provided RPC or default to public
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.client = Client(self.rpc_url)
        self.http_client = httpx.Client(timeout=15.0, follow_redirects=True)

    def get_metadata(self, mint_address: str) -> Optional[Dict]:
        """Get token metadata from blockchain + IPFS"""
        try:
            # Get metadata account PDA (Program Derived Address)
            metadata_pda = self._get_metadata_pda(mint_address)

            # Fetch account data from blockchain
            response = self.client.get_account_info(metadata_pda)

            if not response.value:
                print(f"[DEBUG] No metadata account found for {mint_address}")
                return None

            account_data = response.value.data

            # Parse metadata structure
            metadata = self._parse_metadata(account_data)

            if not metadata:
                return None

            # Fetch JSON from URI (usually IPFS)
            uri = metadata.get('uri', '').strip().rstrip('\x00')

            if uri:
                json_data = self._fetch_uri(uri)
                if json_data:
                    # Extract social links
                    return {
                        'name': metadata.get('name', '').strip().rstrip('\x00'),
                        'symbol': metadata.get('symbol', '').strip().rstrip('\x00'),
                        'uri': uri,
                        'twitter': json_data.get('twitter'),
                        'telegram': json_data.get('telegram'),
                        'website': json_data.get('website'),
                        'description': json_data.get('description', ''),
                        'image': json_data.get('image')
                    }
                else:
                    # IPFS failed but we still have on-chain metadata
                    print(f"[DEBUG] Could not fetch IPFS data, returning on-chain metadata only")
                    return metadata

            return metadata

        except Exception as e:
            print(f"[DEBUG] Metadata fetch error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_metadata_pda(self, mint_address: str) -> Pubkey:
        """Calculate metadata PDA (Program Derived Address)"""
        # Metaplex Token Metadata Program ID
        METADATA_PROGRAM_ID = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")

        mint_pubkey = Pubkey.from_string(mint_address)

        # PDA derivation: [b"metadata", metadata_program_id, mint_pubkey]
        seeds = [
            b"metadata",
            bytes(METADATA_PROGRAM_ID),
            bytes(mint_pubkey)
        ]

        pda, bump = Pubkey.find_program_address(seeds, METADATA_PROGRAM_ID)
        return pda

    def _parse_metadata(self, data: bytes) -> Optional[Dict]:
        """Parse on-chain metadata structure"""
        try:
            # Skip first byte (key = 4 for Metadata account)
            offset = 1

            # Update authority (32 bytes)
            offset += 32

            # Mint (32 bytes)
            offset += 32

            # Name (variable length string with 4-byte length prefix)
            name_len = int.from_bytes(data[offset:offset+4], 'little')
            offset += 4
            name = data[offset:offset+name_len].decode('utf-8', errors='ignore')
            offset += name_len

            # Symbol (variable length string)
            symbol_len = int.from_bytes(data[offset:offset+4], 'little')
            offset += 4
            symbol = data[offset:offset+symbol_len].decode('utf-8', errors='ignore')
            offset += symbol_len

            # URI (variable length string)
            uri_len = int.from_bytes(data[offset:offset+4], 'little')
            offset += 4
            uri = data[offset:offset+uri_len].decode('utf-8', errors='ignore')

            return {
                'name': name,
                'symbol': symbol,
                'uri': uri
            }

        except Exception as e:
            print(f"[DEBUG] Parse metadata error: {e}")
            return None

    def _fetch_uri(self, uri: str) -> Optional[Dict]:
        """Fetch JSON metadata from URI (IPFS or Arweave)"""
        try:
            # Convert IPFS URIs to HTTP gateway
            if uri.startswith('ipfs://'):
                uri = uri.replace('ipfs://', 'https://ipfs.io/ipfs/')

            response = self.http_client.get(uri)

            if response.status_code == 200:
                # Check if response is JSON (not HTML error page)
                content_type = response.headers.get('content-type', '')
                if 'application/json' not in content_type and 'text/html' in content_type:
                    print(f"[DEBUG] IPFS returned HTML instead of JSON (gateway error)")
                    return None

                try:
                    return response.json()
                except Exception as json_error:
                    print(f"[DEBUG] Failed to parse JSON from {uri[:50]}...: {json_error}")
                    return None

            return None

        except Exception as e:
            print(f"[DEBUG] URI fetch error: {e}")
            return None

    def close(self):
        """Close HTTP client"""
        self.http_client.close()
