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
        
        prompt = f"""You are a regex expert. Generate a precise regular expression for the following requirement:

USER REQUEST: "{user_input}"

Please provide:
Only The regex pattern
Analyze the user prompt and give accurate regex, nothing else than that.

Format your response as:
REGEX: [your regex pattern]

Focus on accuracy and practical usage."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 400
        }
        
        try:
            print(f"🔑 Making API call to: {self.base_url}")
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            print(f"📡 API Response Status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            print(f"🤖 AI Raw Response: '{ai_response}'")
            
            regex_pattern = self.extract_regex_from_response(ai_response)
            print(f"🎯 Extracted Pattern: '{regex_pattern}'")
            
            return {
                "success": True,
                "regex": regex_pattern,
                "full_response": ai_response
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API Request Error: {str(e)}")
            return {
                "success": False,
                "error": f"API Request failed: {str(e)}",
                "regex": None
            }
        except Exception as e:
            print(f"❌ Unexpected Error: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "regex": None
            }
    
    def extract_regex_from_response(self, response):
        """Extract regex pattern from AI response"""
        # Clean the response
        cleaned_response = response.strip()
        
        print(f"🔍 Extracting regex from: '{cleaned_response}'")
        
        # Strategy 1: Try to find pattern after "REGEX:" label
        regex_match = re.search(r'REGEX:\s*(.+)', response, re.IGNORECASE)
        if regex_match:
            extracted = regex_match.group(1).strip()
            print(f"✅ Found with REGEX: label: {extracted}")
            return extracted
        
        # Strategy 2: Look for content in backticks
        code_match = re.search(r'`([^`]+)`', response)
        if code_match:
            extracted = code_match.group(1).strip()
            print(f"✅ Found in backticks: {extracted}")
            return extracted
        
        # Strategy 3: Look for regex-like patterns
        pattern_match = re.search(r'([\\^$.*+?{}[\]|()\-].*)', response)
        if pattern_match:
            extracted = pattern_match.group(1).strip()
            print(f"✅ Found regex-like pattern: {extracted}")
            return extracted
        
        # Strategy 4: Try to extract based on user input context (enhanced fallback)
        return self.generate_fallback_pattern(response)
    
    def generate_fallback_pattern(self, response):
        """Generate fallback patterns based on common requests"""
        response_lower = response.lower()
        
        print(f"🔍 Looking for fallback pattern for: '{response_lower}'")
        
        # Enhanced fallback patterns with better detection
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
            'password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
            'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            'credit card': r'^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$',
            'zip': r'^\d{5}(-\d{4})?$',
            'ssn': r'^\d{3}-\d{2}-\d{4}$',
        }
        
        # Check if the response contains common patterns
        for keyword, pattern in fallback_patterns.items():
            if keyword in response_lower:
                print(f"✅ Found fallback pattern for '{keyword}': {pattern}")
                return pattern
        
        # If no pattern found, return the error message for frontend to handle
        print("⚠️ Could not extract regex pattern")
        return "Could not extract regex pattern"
    
    def test_regex(self, pattern, test_string):
        """Test regex pattern against a string"""
        try:
            matches = re.findall(pattern, test_string)
            return {
                "success": True,
                "matches": matches,
                "match_count": len(matches),
                "is_valid": True
            }
        except re.error as e:
            return {
                "success": False,
                "error": f"Invalid regex: {str(e)}",
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
    print("✅ Smart Regex Generator initialized")

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Smart AI Regex Generator",
        "powered_by": "DeepSeek R1",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "generate": "/api/generate (POST)",
            "test": "/api/test (POST)",
            "examples": "/api/examples (GET)",
            "health": "/ (GET)"
        }
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
        
        print(f"📝 Generating regex for: '{user_prompt}'")
        
        # Generate regex
        result = generator.generate_regex(user_prompt)
        
        # Frontend expects these exact fields
        response_data = {
            "success": result["success"],
            "prompt": user_prompt,
            "regex": result["regex"],
            "full_response": result.get("full_response", ""),
            "timestamp": datetime.now().isoformat()
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
        
        # Frontend expects these exact fields
        response_data = {
            "success": result["success"],
            "regex": regex_pattern,
            "test_string": test_string,
            "matches": result.get("matches", []),
            "match_count": result.get("match_count", 0),
            "is_valid": result.get("is_valid", False),
            "timestamp": datetime.now().isoformat()
        }
        
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
            "Email with specific domain validation"
        ],
        "phone": [
            "US phone numbers with area code",
            "International phone format",
            "Phone numbers with extensions"
        ],
        "dates": [
            "Match dates in MM/DD/YYYY format",
            "European date format DD-MM-YYYY",
            "ISO date format YYYY-MM-DD"
        ],
        "web": [
            "Extract URLs from text",
            "Match IPv4 addresses",
            "Find domain names"
        ],
        "finance": [
            "Credit card numbers",
            "US social security numbers",
            "Bank account numbers"
        ],
        "text": [
            "Words starting with capital letter",
            "Extract hashtags from text",
            "Match alphanumeric codes"
        ],
        "security": [
            "Strong password validation",
            "Extract IP addresses from logs",
            "API key patterns"
        ]
    }
    
    return jsonify({
        "examples": examples,
        "total_categories": len(examples),
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
