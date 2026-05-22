"""Port of src/utils/hooks/ssrfGuard.ts - SSRF guard for HTTP hooks."""
from __future__ import annotations
import re
import socket
import struct
from typing import Optional


def is_blocked_address(address: str) -> bool:
    """Returns True if the address is in a range that HTTP hooks should not reach.
    
    Blocked: private, link-local, cloud metadata ranges.
    Allowed: loopback (127.x, ::1), public internet.
    """
    # Check if valid IPv4
    try:
        socket.inet_pton(socket.AF_INET, address)
        return _is_blocked_v4(address)
    except (socket.error, OSError):
        pass
    # Check if valid IPv6
    try:
        socket.inet_pton(socket.AF_INET6, address)
        return _is_blocked_v6(address)
    except (socket.error, OSError):
        pass
    return False


# Alias for TS-style callers
isBlockedAddress = is_blocked_address


def _is_blocked_v4(address: str) -> bool:
    parts = address.split('.')
    if len(parts) != 4:
        return False
    try:
        a, b, c, d = [int(x) for x in parts]
    except ValueError:
        return False
    if any(n < 0 or n > 255 for n in [a, b, c, d]):
        return False

    # Loopback explicitly allowed
    if a == 127:
        return False
    # 0.0.0.0/8 "this" network
    if a == 0:
        return True
    # 10.0.0.0/8 private
    if a == 10:
        return True
    # 169.254.0.0/16 link-local, cloud metadata
    if a == 169 and b == 254:
        return True
    # 172.16.0.0/12 private
    if a == 172 and 16 <= b <= 31:
        return True
    # 100.64.0.0/10 shared address space / CGNAT
    if a == 100 and 64 <= b <= 127:
        return True
    # 192.168.0.0/16 private
    if a == 192 and b == 168:
        return True
    return False


def _is_blocked_v6(address: str) -> bool:
    lower = address.lower()
    # ::1 loopback explicitly allowed
    if lower == '::1':
        return False
    # :: unspecified
    if lower == '::':
        return True

    # Check for IPv4-mapped IPv6
    mapped = _extract_mapped_ipv4(lower)
    if mapped is not None:
        return _is_blocked_v4(mapped)

    # fc00::/7 unique local
    if lower.startswith('fc') or lower.startswith('fd'):
        return True

    # fe80::/10 link-local
    first_hextet = lower.split(':')[0] if ':' in lower else lower
    if len(first_hextet) == 4:
        try:
            val = int(first_hextet, 16)
            if 0xfe80 <= val <= 0xfebf:
                return True
        except ValueError:
            pass

    return False


def _expand_ipv6_groups(addr: str) -> Optional[list]:
    """Expand :: notation and optional trailing dotted-decimal to 8 hex groups."""
    tail_hextets: list = []

    # Handle trailing dotted-decimal IPv4
    if '.' in addr:
        last_colon = addr.rfind(':')
        v4 = addr[last_colon + 1:]
        addr = addr[:last_colon]
        octets = v4.split('.')
        if len(octets) != 4:
            return None
        try:
            nums = [int(o) for o in octets]
        except ValueError:
            return None
        if any(n < 0 or n > 255 for n in nums):
            return None
        tail_hextets = [(nums[0] << 8) | nums[1], (nums[2] << 8) | nums[3]]

    # Expand ::
    dbl = addr.find('::')
    if dbl == -1:
        head = addr.split(':') if addr else []
        tail: list = []
    else:
        head_str = addr[:dbl]
        tail_str = addr[dbl + 2:]
        head = head_str.split(':') if head_str else []
        tail = tail_str.split(':') if tail_str else []

    target = 8 - len(tail_hextets)
    fill = target - len(head) - len(tail)
    if fill < 0:
        return None

    hex_groups = head + ['0'] * fill + tail
    try:
        result = [int(h, 16) for h in hex_groups]
    except ValueError:
        return None
    if any(n < 0 or n > 0xffff for n in result):
        return None
    result.extend(tail_hextets)
    return result if len(result) == 8 else None


def _extract_mapped_ipv4(addr: str) -> Optional[str]:
    """Extract embedded IPv4 from IPv4-mapped IPv6 (::ffff:a.b.c.d)."""
    groups = _expand_ipv6_groups(addr)
    if not groups or len(groups) != 8:
        return None
    # IPv4-mapped: first 5 groups zero, group[5] = 0xffff
    if groups[:5] == [0, 0, 0, 0, 0] and groups[5] == 0xffff:
        hi = groups[6]
        lo = groups[7]
        return f"{(hi >> 8) & 0xff}.{hi & 0xff}.{(lo >> 8) & 0xff}.{lo & 0xff}"
    return None


def ssrf_guarded_lookup(hostname: str) -> str:
    """Resolve hostname and raise if it resolves to a blocked address.
    
    Returns the resolved IP string on success, raises ValueError if blocked.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"DNS lookup failed for {hostname}: {e}") from e

    for info in infos:
        addr = info[4][0]
        if is_blocked_address(addr):
            raise ValueError(
                f"SSRF guard: {hostname} resolved to blocked address {addr}"
            )
    # Return the first resolved address
    if infos:
        return infos[0][4][0]
    raise ValueError(f"No addresses found for {hostname}")


ssrfGuardedLookup = ssrf_guarded_lookup