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
            "health": "/ (GET)"
        }
    })

@app.route('/api/generate', methods=['POST'])
def generate_regex():
    """Generate regex from user input"""
    if not generator:
        return jsonify({
            "success": False,
            "error": "API key not configured"
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
        
        # Generate regex
        result = generator.generate_regex(user_prompt)
        
        response_data = {
            "success": result["success"],
            "prompt": user_prompt,
            "regex": result["regex"],
            "timestamp": datetime.now().isoformat()
        }
        
        if not result["success"]:
            response_data["error"] = result["error"]
            return jsonify(response_data), 500
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
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
        
        regex_pattern = data['regex']
        test_string = data['test_string']
        
        if not generator:
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
                    "is_valid": False
                }
        else:
            result = generator.test_regex(regex_pattern, test_string)
        
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
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
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
        "available_endpoints": ["/", "/api/generate", "/api/test", "/api/examples"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
