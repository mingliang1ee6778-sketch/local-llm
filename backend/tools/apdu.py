def normalize_hex(value: str) -> str:
    cleaned = "".join(ch for ch in value if ch not in " \n\r\t:")
    if len(cleaned) % 2:
        raise ValueError("Hex input must contain an even number of digits")
    int(cleaned or "0", 16)
    return cleaned.upper()


def parse_apdu(apdu_hex: str) -> dict:
    data = bytes.fromhex(normalize_hex(apdu_hex))
    if len(data) < 4:
        raise ValueError("APDU must contain at least CLA INS P1 P2")
    result = {
        "cla": f"{data[0]:02X}",
        "ins": f"{data[1]:02X}",
        "p1": f"{data[2]:02X}",
        "p2": f"{data[3]:02X}",
        "lc": None,
        "data": "",
        "le": None,
    }
    if len(data) == 4:
        return result
    if len(data) == 5:
        result["le"] = data[4]
        return result
    lc = data[4]
    body_end = 5 + lc
    if len(data) < body_end:
        raise ValueError("APDU Lc is longer than the provided data")
    result["lc"] = lc
    result["data"] = data[5:body_end].hex().upper()
    if len(data) > body_end:
        result["le"] = data[body_end]
    return result


def parse_tlv(tlv_hex: str) -> list[dict]:
    data = bytes.fromhex(normalize_hex(tlv_hex))
    items: list[dict] = []
    offset = 0
    while offset < len(data):
        tag_start = offset
        offset += 1
        if data[tag_start] & 0x1F == 0x1F:
            while offset < len(data) and data[offset] & 0x80:
                offset += 1
            offset += 1
        tag = data[tag_start:offset].hex().upper()
        if offset >= len(data):
            raise ValueError(f"Missing length for tag {tag}")
        length_byte = data[offset]
        offset += 1
        if length_byte & 0x80:
            length_size = length_byte & 0x7F
            length = int.from_bytes(data[offset : offset + length_size], "big")
            offset += length_size
        else:
            length = length_byte
        value = data[offset : offset + length]
        if len(value) != length:
            raise ValueError(f"Value for tag {tag} is shorter than declared length")
        offset += length
        items.append({"tag": tag, "length": length, "value": value.hex().upper()})
    return items
