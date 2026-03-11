import requests
import json
import sys
import datetime
import re
import argparse
from hashy import cachy

MISSING_FILE_MSG = "Usage: python mse_generate.py <filename>"
RESULTS_FILE_NAME = "results.txt"
FINISHED_MSG = f"Finished! The formatted file is in {RESULTS_FILE_NAME}"

def parse_type_line(type_line):
	"""Parse type line into supertype and subtype."""
	if not type_line:
		return "", ""
	
	# Split on " — " to separate supertype and subtype
	if " — " in type_line:
		supertype, subtype = type_line.split(" — ", 1)
		return supertype.strip(), subtype.strip()
	return type_line.strip(), ""

def strip_reminder_text(text):
	"""Remove all reminder text (content inside parentheses) from oracle text."""
	if not text:
		return text
	
	# Handle nested parentheses by iteratively removing innermost pairs
	result = text
	while True:
		# Remove parentheses with their content
		# Capture space before and after to clean up properly
		new_result = re.sub(r'([ \t]*)\([^()]*\)([ \t]*)', r'\1\2', result)
		if new_result == result:
			break  # No more parentheses found
		result = new_result
	
	# Clean up any remaining extra spaces, but preserve newlines
	# Collapse multiple spaces/tabs to single space (but preserve newlines)
	result = re.sub(r'[ \t]+', ' ', result)
	# Strip leading/trailing whitespace (including newlines at start/end)
	result = result.strip()
	return result

def convert_keywords_to_tags(text):
	"""Convert Magic keywords to MSE keyword tags."""
	# Common keyword mappings
	keyword_tags = {
		'mills': '<kw-a><nospellcheck><key><param-mill>mills</param-mill> <param-one_word>two</param-one_word> car<param-*s>ds</param-*s></key></nospellcheck></kw-a>',
		'Mill': '<kw-a><nospellcheck><key><param-mill>mills</param-mill> <param-one_word>two</param-one_word> car<param-*s>ds</param-*s></key></nospellcheck></kw-a>',
	}
	
	# Simple approach: just wrap the entire text
	# In a real implementation, you'd parse keywords more carefully
	return text

def parse_saga_text(oracle_text):
	"""Parse saga oracle text into chapter text and level texts."""
	if not oracle_text:
		return "", "", [], ""
	
	lines = oracle_text.split('\n')
	chapter_text = ""
	rule_lines = []
	level_texts_dict = {}  # Maps chapter to text
	unique_texts = []  # List of unique text values in order
	
	# Extract chapter text (first line in parentheses)
	if lines and lines[0].strip().startswith('('):
		chapter_text = lines[0].strip()
		lines = lines[1:]
	
	# Parse chapter lines (like "I, II — Text" or "III — Text")
	for line in lines:
		line = line.strip()
		if not line:
			continue
		
		# Match patterns like "I, II —" or "III —" at the start
		match = re.match(r'^([IVX,—\s]+)—\s*(.*)$', line)
		if match:
			chapters = match.group(1).strip()
			text = match.group(2).strip()
			
			# Parse which chapters this applies to
			chapters_list = re.findall(r'[IVX]+', chapters)
			
			# Add to rule_lines with symbol tags
			if len(chapters_list) == 1:
				# Single chapter like "III"
				chapter_sym = chapters_list[0]
				rule_lines.append(f"<sym-auto>{chapter_sym}</sym-auto> — {text}")
			else:
				# Multiple chapters like "I, II"
				first_chapter = chapters_list[0]
				other_chapters = ", ".join(chapters_list[1:])
				rule_lines.append(f"<sym-auto>{first_chapter}</sym-auto>, {other_chapters} — {text}")
			
			# Store text for each chapter
			for chapter in chapters_list:
				level_texts_dict[chapter] = text
			
			# Add to unique texts if we haven't seen this text yet
			if text not in unique_texts:
				unique_texts.append(text)
		else:
			# Not a chapter line, might be additional rule text
			rule_lines.append(line)
	
	rule_text = "\n\t\t".join(rule_lines)
	
	return chapter_text, rule_text, unique_texts, oracle_text

def get_subtype_tag(super_type):
	"""Determine the appropriate subtype tag based on supertype."""
	super_type_lower = super_type.lower()
	if "instant" in super_type_lower or "sorcery" in super_type_lower:
		return "word-list-spell"
	elif "land" in super_type_lower:
		return "word-list-land"
	elif "creature" in super_type_lower:
		return "word-list-race"
	elif "planeswalker" in super_type_lower:
		return "word-list-race"  # MSE uses race for planeswalker subtypes too
	elif "enchantment" in super_type_lower:
		return "word-list-race"
	elif "artifact" in super_type_lower:
		return "word-list-race"
	else:
		return "word-list-spell"  # Default fallback

def templated_card_saga(card, include_flavor_text=False):
	"""Generate MSE template for saga cards."""
	level_texts = card.get("level_texts", [])
	num_boxes = len(level_texts)
	
	# Determine styling based on number of boxes
	if num_boxes == 2:
		has_styling = "true"
		styling_data = """
	styling_data:
		chapter_textboxes: two
		text_box_mana_symbols: magic-mana-small.mse-symbol-font
		overlay: """
	else:
		has_styling = "false"
		styling_data = ""
	
	# Build level text fields
	level_fields = ""
	for i, level_text in enumerate(level_texts, 1):
		level_fields += f"""
	level_{i}_text: {level_text}"""
	
	# Add empty level fields if there are fewer than 3 levels
	for i in range(num_boxes + 1, 4):
		level_fields += f"""
	level_{i}_text:"""
	
	# If 2 boxes, duplicate level_2_text to level_3_text
	if num_boxes == 2 and len(level_texts) >= 2:
		level_fields += f"""
	level_3_text: {level_texts[1]}"""
	
	# Build special_text (includes chapter text + full rule text)
	special_text_content = f"\t\t<i-auto>{card.get('chapter_text', '')}</i-auto>"
	if card.get("rule_text"):
		# Add the rule text lines
		for line in card["rule_text"].split('\n'):
			if line.strip():
				special_text_content += f"\n\t\t{line.strip()}"
	
	# Conditionally include flavor text
	flavor_text_line = ""
	if include_flavor_text:
		flavor_text_line = f"\n\tflavor_text: <i-flavor>{card.get('flavor_text', '')}</i-flavor>"
	
	text = f"""
card:
	stylesheet: m15-saga
	stylesheet_version: 2024-09-23
	has_styling: {has_styling}{styling_data}
	notes: 
	time_created: {card["time"]}
	time_modified: {card["time"]}
	special_text:
{special_text_content}
	name: !! {card["name"]}
	alias: {card["name"]}
	casting_cost: {card["cost"]}
	image: 
	image_2: 
	mainframe_image: 
	mainframe_image_2: 
	super_type: <word-list-type-en>{card["super_type"]}</word-list-type-en>
	sub_type: <word-list-enchantment>{card.get("sub_type", "")}</word-list-enchantment><soft><atom-sep> </atom-sep></soft><word-list-enchantment></word-list-enchantment>
	sub_type_2: 
	sub_type_3: 
	sub_type_4: 
	rarity: {card["rarity"]}
	chapter_text: <i-auto>{card.get("chapter_text", "")}</i-auto>
	rule_text:
		{card["rule_text"]}		{flavor_text_line}{level_fields}
	card_code_text: 
	card_code_text_2: 
	card_code_text_3: 
	copyright: 
	copyright_2: 
	copyright_3: """
	return text

def templated_card(card, include_flavor_text=False):
	is_dfc = card.get("is_dfc", False)
	is_saga = card.get("is_saga", False)
	is_adventure = card.get("is_adventure", False)
	
	if is_saga:
		return templated_card_saga(card, include_flavor_text)
	
	stylesheet_string = ""
	if is_dfc or is_adventure:
		if is_adventure:
			stylesheet = "m15-adventure"
			stylesheet_version = "2024-05-27"
		else:
			stylesheet = "m15-mainframe-dfc"
			stylesheet_version = "2024-09-06"
		stylesheet_string = f"""
	stylesheet: {stylesheet}
	stylesheet_version: {stylesheet_version}
	"""
		# Double-faced card or adventure card format
		# Determine stylesheet based on card type
		if is_adventure:
			stylesheet = "m15-adventure"
			stylesheet_version = "2024-05-27"
		else:
			stylesheet = "m15-mainframe-dfc"
			stylesheet_version = "2024-09-06"
		
		flavor_lines = ""
		if include_flavor_text:
			flavor_lines = f"""
	flavor_text: <i-flavor>{card["flavor_text"]}</i-flavor>
	flavor_text_2: <i-flavor>{card.get("flavor_text_2", "")}</i-flavor>"""
		
		text = f"""
card:{stylesheet_string}
	has_styling: false
	notes: 
	time_created: {card["time"]}
	time_modified: {card["time"]}
	name: !! {card["name"]}
	name_2: {card.get("name_2", "")}
	alias: {card["alias"]}
	casting_cost: {card["cost"]}
	image: 
	image_2: 
	mainframe_image: 
	mainframe_image_2: 
	super_type: <word-list-type-en>{card["super_type"]}</word-list-type-en>
	super_type_2: <word-list-type-en>{card.get("super_type_2", "")}</word-list-type-en>
	sub_type: <{card.get("sub_type_tag", "word-list-spell")}>{card.get("sub_type", "")}</{card.get("sub_type_tag", "word-list-spell")}>
	sub_type_2: <{card.get("sub_type_tag_2", "word-list-land")}>{card.get("sub_type_2", "")}</{card.get("sub_type_tag_2", "word-list-land")}>
	sub_type_3: 
	sub_type_4: 
	rarity: {card["rarity"]}
	rule_text: {card["rule_text"]}
	rule_text_2:
		{card.get("rule_text_2", "")}		{flavor_lines}
	card_code_text: 
	card_code_text_2: 
	card_code_text_3: """
	else:
		# Single-faced card format
		flavor_line = ""
		if include_flavor_text:
			flavor_line = f"""
	flavor text: <i-flavor>{card["flavor_text"]}</i-flavor>"""
		
		text = f"""
card:
	has styling: false
	notes: 
	time created: {card["time"]}
	time modified: {card["time"]}
	name: !! {card["name"]}
	alias: {card["name"]}
	casting cost: {card["cost"]}
	image:
	super type: <word-list-type>{card["super_type"]}</word-list-type>
	sub type: <word-list-race>{card.get("sub_type", "")}</word-list-race>
	rarity: {card["rarity"]}
	rule text:
		{card["rule_text"]}		{flavor_line}"""

		if all(card.get(key) is not None for key in ["power", "toughness"]):
			text += f"""
	power: {card["power"]}
	toughness: {card["toughness"]}"""

		text += f"""
	card code text: 
	copyright: 
	image 2: 
	copyright 2: 
	copyright 3: 
	mainframe image: 
	mainframe image 2:"""
	return text

def gen_card(raw_info):
	# Check if this is an adventure card first (adventures also have card_faces)
	is_adventure = raw_info.get("layout") == "adventure"
	
	# Handle double-faced cards (modal DFC, transform, etc.) and adventure cards
	card_faces = raw_info.get("card_faces", [])
	
	if card_faces:
		# Double-faced card - separate data for each face
		face1 = card_faces[0]
		face2 = card_faces[1] if len(card_faces) > 1 else {}
		
		# Get full card name (includes both faces separated by " // ")
		full_name = raw_info.get("name", "")
		name_parts = full_name.split(" // ", 1)
		name1 = name_parts[0] if name_parts else ""
		name2 = name_parts[1] if len(name_parts) > 1 else face2.get("name", "")
		
		# Mana cost from first face (usually the spell side)
		mana_cost = face1.get("mana_cost", "") or ""
		cost = mana_cost.replace("{", "").replace("}", "")
		
		# Parse type lines for each face
		type1 = face1.get("type_line", "") or ""
		type2 = face2.get("type_line", "") or ""
		super_type1, sub_type1 = parse_type_line(type1)
		super_type2, sub_type2 = parse_type_line(type2)
		sub_type_tag1 = get_subtype_tag(super_type1)
		sub_type_tag2 = get_subtype_tag(super_type2)
		
		# Oracle text for each face
		oracle1 = face1.get("oracle_text", "") or ""
		oracle2 = face2.get("oracle_text", "") or ""
		# Strip reminder text (parentheses) from oracle text
		oracle1 = strip_reminder_text(oracle1)
		oracle2 = strip_reminder_text(oracle2)
		# First face rule text should be inline (replace newlines with spaces), second face should be indented
		rule_text1 = oracle1.replace("\n", " ").replace("{", "").replace("}", "").strip()
		rule_text2 = oracle2.replace("\n", "\n\t\t").replace("{", "").replace("}", "")
		
		# Flavor text for each face
		flavor1 = face1.get("flavor_text", "") or ""
		flavor2 = face2.get("flavor_text", "") or ""
		
		# Power/toughness (usually only on one face)
		power = face1.get("power") or face2.get("power") or raw_info.get("power")
		toughness = face1.get("toughness") or face2.get("toughness") or raw_info.get("toughness")
		
		return {
			"is_dfc": not is_adventure,  # Adventure cards are not DFCs
			"is_adventure": is_adventure,
			"name": name1,
			"name_2": name2,
			"alias": full_name,
			"cost": cost,
			"super_type": super_type1,
			"super_type_2": super_type2,
			"sub_type": sub_type1,
			"sub_type_2": sub_type2,
			"sub_type_tag": sub_type_tag1,
			"sub_type_tag_2": sub_type_tag2,
			"rule_text": rule_text1,
			"rule_text_2": rule_text2,
			"flavor_text": flavor1,
			"flavor_text_2": flavor2,
			"power": power,
			"toughness": toughness,
			"rarity": raw_info.get("rarity", "").lower() if raw_info.get("rarity") else "",
			"time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		}
	else:
		# Single-faced card - use top-level fields
		mana_cost = raw_info.get("mana_cost", "") or raw_info.get("manaCost", "")
		cost = mana_cost.replace("{", "").replace("}", "")
		
		type_line = raw_info.get("type_line", "") or raw_info.get("type", "")
		super_type, sub_type = parse_type_line(type_line)
		
		# Check if this is a saga card
		is_saga = raw_info.get("layout") == "saga" or "Saga" in sub_type
		
		oracle_text = raw_info.get("oracle_text", "") or raw_info.get("text", "")
		
		if is_saga:
			# Parse saga text
			chapter_text, rule_text, level_texts, full_oracle = parse_saga_text(oracle_text)
			rule_text = rule_text.replace("{", "").replace("}", "")
		else:
			# Strip reminder text (parentheses) from oracle text
			oracle_text = strip_reminder_text(oracle_text)
			rule_text = oracle_text.replace("\n", "\n\t\t").replace("{", "").replace("}", "")
			chapter_text = ""
			level_texts = []
		
		flavor_text = raw_info.get("flavor_text", "") or raw_info.get("flavor", "") or ""
		
		power = raw_info.get("power")
		toughness = raw_info.get("toughness")
		
		result = {
			"is_dfc": False,
			"is_saga": is_saga,
			"name": raw_info.get("name"),
			"cost": cost,
			"super_type": super_type,
			"sub_type": sub_type,
			"rule_text": rule_text,
			"flavor_text": flavor_text,
			"power": power,
			"toughness": toughness,
			"rarity": raw_info.get("rarity", "").lower() if raw_info.get("rarity") else "",
			"time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		}
		
		if is_saga:
			result["chapter_text"] = chapter_text
			result["level_texts"] = level_texts
		
		return result

def extract_card_name(full_name):
	"""Extract card name from the full card name string."""
	# Pattern to match: "1 Card Name (SET) NUMBER" - extract the card name part
	match = re.match(r'\d+\s+(.*?)\s+\([^)]+\)', full_name)
	if match:
		return match.group(1).strip()
	return None

def extract_set_and_number(full_name):
	"""Extract set code and card number from the full card name string."""
	# Pattern to match: "1 Card Name (SET) NUMBER" with optional markers like *F* or trailing letters
	match = re.match(r'\d+\s+.*?\s+\(([^)]+)\)\s+(\S+)', full_name)
	if match:
		set_code = match.group(1).lower()  # Convert to lowercase for API
		card_number = match.group(2)
		# Remove trailing lowercase letters (like 'p' in '182p') for fallback API call
		# Card numbers may include hyphens (like 'DTK-172')
		card_number_clean = re.sub(r'[a-z]+$', '', card_number)  # Remove trailing lowercase letters
		return set_code, card_number, card_number_clean if card_number_clean and card_number_clean != card_number else None
	return None, None, None

def fetch_card_data(full_card_name):
	"""Fetch card from Scryfall API using set code and card number."""
	# Extract set code and card number
	set_code, card_number, card_number_clean = extract_set_and_number(full_card_name)
	if not set_code or not card_number:
		print(f"Could not extract set code and card number from: {full_card_name}")
		return None
	
	# Try with full card number first (including trailing letters like '182p')
	result = download_card_data(set_code, card_number)

	if result is not None:
		return result
	
	# If that fails and we have a cleaned version, try that
	if card_number_clean:
		return download_card_data(set_code, card_number_clean)
	
	return None

@cachy()
def download_card_data(set_code, card_number):
	try:
		# Construct direct API URL
		api_url = f"https://api.scryfall.com/cards/{set_code}/{card_number}"
		response = requests.get(api_url, headers={'User-Agent': 'VTuberMatchViewer/1.0'})
		
		if response.status_code == 404:
			# Card not found - return None so caller can try fallback
			return None
		
		response.raise_for_status()
		# Get the card data
		return response.json()

	except requests.exceptions.HTTPError as e:
		if e.response.status_code == 404:
			return None
		print(f"Error fetching card data: {e}")
		return None
	except Exception as e:
		print(f"Error fetching card data: {e}")
		return None
		
def get_card_info(name):
	card_data = fetch_card_data(name)
	
	if card_data is None:
		return None
	
	# print(card_data)
	
	parsed_card = gen_card(card_data)
	return parsed_card

def gen_text(card_names, debug=False, include_flavor_text=False):
	full_text = ""
	for card_name in card_names:
		if debug:
			print(f"Getting info for {card_name}")
		card_info = get_card_info(card_name)
		if card_info is None:
			print(f"not found: {card_name}")
			# Extract card name and create minimal card entry
			extracted_name = extract_card_name(card_name)
			if extracted_name:
				minimal_card = {
					"name": extracted_name,
					"cost": "",
					"type": "",
					"rule_text": "",
					"flavor_text": "",
					"power": None,
					"toughness": None,
					"rarity": "",
					"time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				}
				full_text += templated_card(minimal_card, include_flavor_text)
			continue
		full_text += templated_card(card_info, include_flavor_text)
	return full_text


def read_names_from_file(filename):
	with open(filename, "r", encoding='utf-8') as f:
		lines = f.readlines()
	card_names = [line.strip() for line in lines if line.strip()]
	return card_names


def write_to_file(filename, text):
	f = open(filename, "w+", encoding='utf-8')
	f.write(text)
	f.close()


def run():
	parser = argparse.ArgumentParser(description='Generate MSE card set from card list')
	parser.add_argument('filename', help='Input file containing card names')
	parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')
	parser.add_argument('--flavor-text', action='store_true', help='Include flavor text in card templates')
	
	args = parser.parse_args()
	
	card_names = read_names_from_file(args.filename)
	if args.debug:
		print(card_names)
	text = gen_text(card_names, debug=args.debug, include_flavor_text=args.flavor_text)
	write_to_file(RESULTS_FILE_NAME, text)
	print(FINISHED_MSG)

if __name__ == "__main__":
	run()
