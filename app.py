from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import re
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for web interface

class SmartRegexGenerator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "deepseek/deepseek-r1:free"
        
    def generate_regex(self, user_input):
        """Generate regex using DeepSeek R1"""
        
        # Improved prompt that forces better format
        prompt = f"""You are a regex expert. Create a regular expression for: "{user_input}"

IMPORTANT: Respond with ONLY the regex pattern on a single line. No explanations, no formatting, no extra text.

Examples:
- For "email addresses": ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$
- For "phone numbers": ^\\(?[0-9]{{3}}\\)?[-\\.\\s]?[0-9]{{3}}[-\\.\\s]?[0-9]{{4}}$

Your response should be ONLY the regex pattern."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 150
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            regex_pattern = self.extract_regex_from_response(ai_response)
            
            return {
                "success": True,
                "regex": regex_pattern,
                "full_response": ai_response
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"API Request failed: {str(e)}",
                "regex": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "regex": None
            }
    
    def extract_regex_from_response(self, response):
        """Enhanced regex pattern extraction from AI response"""
        
        # Clean the response
        cleaned_response = response.strip()
        
        # Strategy 1: Direct regex pattern (most common with improved prompt)
        # Look for lines that start with regex characters
        lines = cleaned_response.split('\n')
        for line in lines:
            line = line.strip()
            if line and self.looks_like_regex(line):
                return line
        
        # Strategy 2: Look for patterns in common formats
        extraction_patterns = [
            r'REGEX:\s*(.+)',                    # REGEX: pattern
            r'Pattern:\s*(.+)',                  # Pattern: pattern
            r'Expression:\s*(.+)',               # Expression: pattern
            r'`([^`]+)`',                        # `pattern`
            r'(?:regex)?\s*`([^`]+)`\s*',        # `pattern`
            r'/([^/]+)/',                        # /pattern/
            r'^([\\^$.*+?{}[\]|()\-].+)$',       # Lines starting with regex chars
            r'([\\^$.*+?{}[\]|()\-]{2,}.+)',     # Any string with multiple regex chars
        ]
        
        for pattern in extraction_patterns:
            match = re.search(pattern, cleaned_response, re.IGNORECASE | re.MULTILINE)
            if match:
                extracted = match.group(1).strip()
                if self.is_valid_regex(extracted):
                    return extracted
        
        # Strategy 3: Find the longest string that looks like regex
        potential_patterns = []
        words = cleaned_response.split()
        
        for word in words:
            if len(word) > 5 and self.looks_like_regex(word):
                potential_patterns.append(word)
        
        if potential_patterns:
            # Return the longest one (likely the most complete)
            return max(potential_patterns, key=len)
        
        # Strategy 4: Last resort - try to find any regex-like substring
        regex_chars_pattern = r'[\\^$.+?{}[\]|()\-]{3,}[^\\^$.+?{}[\]|()\-\s]*'
        matches = re.findall(regex_chars_pattern, cleaned_response)
        if matches:
            return matches[0]
        
        # Strategy 5: If all else fails, try common patterns based on user input
        return self.generate_fallback_pattern(cleaned_response)
    
    def looks_like_regex(self, text):
        """Check if text looks like a regex pattern"""
        if not text or len(text) < 3:
            return False
        
        # Count regex special characters
        regex_chars = set('\\^$.*+?{}[]|()')
        regex_char_count = sum(1 for char in text if char in regex_chars)
        
        # Should have at least 2 regex characters and reasonable length
        return regex_char_count >= 2 and len(text) <= 200
    
    def is_valid_regex(self, pattern):
        """Test if the pattern is a valid regex"""
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False
    
    def generate_fallback_pattern(self, response):
        """Generate fallback patterns based on common requests"""
        response_lower = response.lower()
        
        fallback_patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$',
            'url': r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.]*))?(?:#(?:\w*))?)?',
            'ip': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
            'date': r'^\d{1,2}/\d{1,2}/\d{4}$',
            'time': r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$',
            'number': r'^\d+$',
            'word': r'^[a-zA-Z]+$',
            'alphanumeric': r'^[a-zA-Z0-9]+$',
        }
        
        for keyword, pattern in fallback_patterns.items():
            if keyword in response_lower:
                return pattern
        
        # Ultimate fallback
        return r'.*'
    
    def test_regex(self, pattern, test_string):
        """Test regex pattern against a string"""
        try:
            # First validate the regex pattern
            compiled_pattern = re.compile(pattern)
            
            # Find all matches
            matches = compiled_pattern.findall(test_string)
            
            # Also get match objects for more detailed info
            match_objects = list(compiled_pattern.finditer(test_string))
            
            # Prepare detailed matches
            detailed_matches = []
            for match_obj in match_objects:
                if match_obj.groups():
                    # If there are groups, return the groups
                    detailed_matches.extend([group for group in match_obj.groups() if group is not None])
                else:
                    # If no groups, return the full match
                    detailed_matches.append(match_obj.group(0))
            
            # Use the more detailed matches if available, otherwise use simple findall
            final_matches = detailed_matches if detailed_matches else matches
            
            return {
                "success": True,
                "matches": final_matches,
                "match_count": len(final_matches),
                "is_valid": True,
                "pattern_info": {
                    "pattern": pattern,
                    "flags": "None",
                    "groups": compiled_pattern.groups
                }
            }
        except re.error as e:
            return {
                "success": False,
                "error": f"Invalid regex pattern: {str(e)}",
                "matches": [],
                "match_count": 0,
                "is_valid": False
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error testing regex: {str(e)}",
                "matches": [],
                "match_count": 0,
                "is_valid": False
            }

# Initialize generator with API key from environment
API_KEY = os.getenv('DEEPSEEK_API_KEY')
if not API_KEY:
    print("⚠️  Warning: DEEPSEEK_API_KEY environment variable not set")
    generator = None
else:
    generator = SmartRegexGenerator(API_KEY)
    print("✅ Smart Regex Generator initialized with enhanced extraction")

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Smart AI Regex Generator",
        "powered_by": "DeepSeek R1",
        "version": "2.0 - Enhanced Extraction",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "generate": "/api/generate (POST)",
            "test": "/api/test (POST)",
            "examples": "/api/examples (GET)",
            "health": "/ (GET)"
        },
        "features": [
            "Enhanced regex extraction",
            "Multiple extraction strategies",
            "Fallback pattern generation",
            "Improved error handling"
        ]
    })

@app.route('/api/generate', methods=['POST'])
def generate_regex():
    """Generate regex from user input"""
    if not generator:
        return jsonify({
            "success": False,
            "error": "API key not configured. Please set DEEPSEEK_API_KEY environment variable."
        }), 500
    
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'prompt' in request body"
            }), 400
        
        user_prompt = data['prompt'].strip()
        
        if not user_prompt:
            return jsonify({
                "success": False,
                "error": "Prompt cannot be empty"
            }), 400
        
        if len(user_prompt) > 500:
            return jsonify({
                "success": False,
                "error": "Prompt too long. Please keep it under 500 characters."
            }), 400
        
        print(f"📝 Generating regex for: '{user_prompt}'")
        
        # Generate regex
        result = generator.generate_regex(user_prompt)
        
        response_data = {
            "success": result["success"],
            "prompt": user_prompt,
            "regex": result["regex"],
            "full_response": result.get("full_response"),
            "timestamp": datetime.now().isoformat(),
            "extraction_successful": result["regex"] != "Could not extract regex pattern" if result["success"] else False
        }
        
        if not result["success"]:
            response_data["error"] = result["error"]
            print(f"❌ Generation failed: {result['error']}")
            return jsonify(response_data), 500
        
        print(f"✅ Generated regex: {result['regex']}")
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"Server error: {str(e)}"
        print(f"💥 Server error: {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/test', methods=['POST'])
def test_regex():
    """Test regex pattern against test string"""
    try:
        data = request.get_json()
        
        if not data or 'regex' not in data or 'test_string' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'regex' or 'test_string' in request body"
            }), 400
        
        regex_pattern = data['regex'].strip()
        test_string = data['test_string']
        
        if not regex_pattern:
            return jsonify({
                "success": False,
                "error": "Regex pattern cannot be empty"
            }), 400
        
        print(f"🧪 Testing regex: '{regex_pattern}' against: '{test_string[:50]}...'")
        
        if generator:
            result = generator.test_regex(regex_pattern, test_string)
        else:
            # Fallback testing without generator
            try:
                matches = re.findall(regex_pattern, test_string)
                result = {
                    "success": True,
                    "matches": matches,
                    "match_count": len(matches),
                    "is_valid": True
                }
            except re.error as e:
                result = {
                    "success": False,
                    "error": f"Invalid regex: {str(e)}",
                    "matches": [],
                    "match_count": 0,
                    "is_valid": False
                }
        
        response_data = {
            "success": result["success"],
            "regex": regex_pattern,
            "test_string": test_string,
            "matches": result.get("matches", []),
            "match_count": result.get("match_count", 0),
            "is_valid": result.get("is_valid", False),
            "timestamp": datetime.now().isoformat()
        }
        
        if "pattern_info" in result:
            response_data["pattern_info"] = result["pattern_info"]
        
        if not result["success"]:
            response_data["error"] = result["error"]
            print(f"❌ Test failed: {result['error']}")
        else:
            print(f"✅ Test successful: {result['match_count']} matches found")
        
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"Server error: {str(e)}"
        print(f"💥 Test error: {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Get example prompts for the regex generator"""
    examples = {
        "email": [
            "Match email addresses",
            "Validate Gmail addresses only",
            "Email with specific domain validation",
            "Extract all emails from text"
        ],
        "phone": [
            "US phone numbers with area code",
            "International phone format",
            "Phone numbers with extensions",
            "Mobile phone numbers only"
        ],
        "dates": [
            "Match dates in MM/DD/YYYY format",
            "European date format DD-MM-YYYY",
            "ISO date format YYYY-MM-DD",
            "Flexible date formats"
        ],
        "web": [
            "Extract URLs from text",
            "Match IPv4 addresses",
            "Find domain names",
            "HTTPS URLs only"
        ],
        "finance": [
            "Credit card numbers",
            "US social security numbers",
            "Bank account numbers",
            "Currency amounts"
        ],
        "text": [
            "Words starting with capital letter",
            "Extract hashtags from text",
            "Match alphanumeric codes",
            "Find quoted text"
        ],
        "security": [
            "Strong password validation",
            "Extract IP addresses from logs",
            "API key patterns",
            "UUID format validation"
        ],
        "validation": [
            "Validate username format",
            "Check postal codes",
            "Verify file extensions",
            "Match specific patterns"
        ]
    }
    
    return jsonify({
        "examples": examples,
        "total_categories": len(examples),
        "total_examples": sum(len(prompts) for prompts in examples.values()),
        "timestamp": datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/api/generate", "/api/test", "/api/examples"],
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "timestamp": datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting Smart Regex Generator on port {port}")
    print(f"🔧 Debug mode: {debug_mode}")
    print(f"🤖 Model: deepseek/deepseek-r1:free")
    print(f"🔑 API Key configured: {'Yes' if API_KEY else 'No'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
