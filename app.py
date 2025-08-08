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
            print(f"🔧 Request data: {json.dumps(data, indent=2)}")
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            print(f"📡 API Response Status: {response.status_code}")
            print(f"📡 Response Headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            result = response.json()
            print(f"📄 Full API Response: {json.dumps(result, indent=2)}")
            
            # Handle different response formats
            ai_response = ""
            if 'choices' in result and len(result['choices']) > 0:
                choice = result['choices'][0]
                
                # Handle different message formats
                if 'message' in choice and 'content' in choice['message']:
                    ai_response = choice['message']['content']
                elif 'text' in choice:
                    ai_response = choice['text']
                else:
                    ai_response = str(choice)
                    
                print(f"🤖 AI Raw Response: '{ai_response}'")
                
                # If response is empty or None, use smart fallback
                if not ai_response or ai_response.strip() == '':
                    print("⚠️ Empty AI response, using smart fallback...")
                    ai_response = "Empty response from AI"
                    regex_pattern = self.generate_smart_fallback(user_input)
                else:
                    regex_pattern = self.extract_regex_from_response(ai_response)
                
                # If extraction still fails, use smart fallback
                if regex_pattern == "Could not extract regex pattern":
                    regex_pattern = self.generate_smart_fallback(user_input)
                
                print(f"🎯 Final Pattern: '{regex_pattern}'")
                
                return {
                    "success": True,
                    "regex": regex_pattern,
                    "full_response": ai_response
                }
            else:
                print("❌ No choices in API response")
                # Use smart fallback when API fails
                regex_pattern = self.generate_smart_fallback(user_input)
                return {
                    "success": True,
                    "regex": regex_pattern,
                    "full_response": "API returned no response, using smart fallback"
                }
                
        except requests.exceptions.RequestException as e:
            print(f"❌ API Request Error: {str(e)}")
            # Use smart fallback on API error
            regex_pattern = self.generate_smart_fallback(user_input)
            return {
                "success": True,
                "regex": regex_pattern,
                "full_response": f"API Error: {str(e)}, using smart fallback"
            }
        except Exception as e:
            print(f"❌ Unexpected Error: {str(e)}")
            # Use smart fallback on any error
            regex_pattern = self.generate_smart_fallback(user_input)
            return {
                "success": True,
                "regex": regex_pattern,
                "full_response": f"Error: {str(e)}, using smart fallback"
            }
    
    def extract_regex_from_response(self, response):
        """Extract regex pattern from AI response"""
        # Try to find pattern after "REGEX:" label
        regex_match = re.search(r'REGEX:\s*(.+)', response, re.IGNORECASE)
        if regex_match:
            return regex_match.group(1).strip()
        
        # Fallback: look for content in backticks or code blocks
        code_match = re.search(r'`([^`]+)`', response)
        if code_match:
            return code_match.group(1).strip()
        
        # Last resort: look for regex-like patterns
        pattern_match = re.search(r'([\\^$.*+?{}[\]|()\-].*)', response)
        if pattern_match:
            return pattern_match.group(1).strip()
        
        return "Could not extract regex pattern"
    
    def generate_smart_fallback(self, user_input):
        """Generate smart fallback patterns based on user input"""
        user_lower = user_input.lower()
        
        print(f"🔍 Generating smart fallback for: '{user_input}'")
        
        # Enhanced pattern matching based on user input
        smart_patterns = {
            # Email patterns
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'gmail': r'^[a-zA-Z0-9._%+-]+@gmail\.com$',
            'yahoo': r'^[a-zA-Z0-9._%+-]+@yahoo\.com$',
            
            # Phone patterns
            'phone': r'^\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$',
            'mobile': r'^\+?1?[0-9]{10}$',
            'international': r'^\+[1-9]\d{1,14}$',
            
            # Date patterns
            'date': r'^\d{1,2}/\d{1,2}/\d{4}$',
            'mm/dd/yyyy': r'^(0[1-9]|1[0-2])/(0[1-9]|[12][0-9]|3[01])/\d{4}$',
            'dd-mm-yyyy': r'^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])-\d{4}$',
            'yyyy-mm-dd': r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$',
            'iso': r'^\d{4}-\d{2}-\d{2}$',
            
            # Web patterns
            'url': r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.]*))?(?:#(?:\w*))?)?',
            'http': r'https?://[^\s]+',
            'domain': r'^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$',
            'ip': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
            'ipv4': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
            
            # Text patterns
            'word': r'^[a-zA-Z]+$',
            'capital': r'^[A-Z][a-z]*$',
            'uppercase': r'^[A-Z]+$',
            'lowercase': r'^[a-z]+$',
            'alphanumeric': r'^[a-zA-Z0-9]+$',
            'hashtag': r'#[a-zA-Z0-9_]+',
            'mention': r'@[a-zA-Z0-9_]+',
            
            # Number patterns
            'number': r'^\d+$',
            'integer': r'^-?\d+$',
            'decimal': r'^\d+\.\d+$',
            'float': r'^-?\d+\.?\d*$',
            'currency': r'^\$?\d{1,3}(,\d{3})*(\.\d{2})?$',
            
            # Finance patterns
            'credit card': r'^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$',
            'creditcard': r'^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$',
            'ssn': r'^\d{3}-\d{2}-\d{4}$',
            'social security': r'^\d{3}-\d{2}-\d{4}$',
            'zip': r'^\d{5}(-\d{4})?$',
            'zipcode': r'^\d{5}(-\d{4})?$',
            'postal': r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$',
            
            # Security patterns
            'password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
            'strong password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
            'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            'api key': r'^[A-Za-z0-9]{32}$',
            'hex': r'^[0-9a-fA-F]+$',
            'hexadecimal': r'^#?[0-9a-fA-F]{6}$',
            
            # Time patterns
            'time': r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$',
            '24hour': r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$',
            '12hour': r'^(0?[1-9]|1[0-2]):[0-5][0-9]\s?(AM|PM)$',
        }
        
        # Check for exact matches first
        for keyword, pattern in smart_patterns.items():
            if keyword in user_lower:
                print(f"✅ Found smart fallback pattern for '{keyword}': {pattern}")
                return pattern
        
        # Check for partial matches (more flexible)
        for keyword, pattern in smart_patterns.items():
            if any(word in user_lower for word in keyword.split()):
                print(f"✅ Found partial match for '{keyword}': {pattern}")
                return pattern
        
        # If no specific pattern found, try to infer from context
        if 'match' in user_lower:
            if 'waqas@gmail.com' in user_lower or '@gmail.com' in user_lower:
                print("✅ Detected email context from example")
                return smart_patterns['email']
            elif any(char in user_lower for char in ['@', '.com', '.org', '.net']):
                print("✅ Detected email context from symbols")
                return smart_patterns['email']
        
        # Ultimate fallback - a very permissive pattern
        print("⚠️ Using ultimate fallback pattern")
        return r'.+'
    
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
