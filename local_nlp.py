import json
import pickle
import numpy as np
import re
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from fuzzywuzzy import fuzz
import random
import os

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')


class LocalNLPProcessor:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.pipeline = None
        self.intents_data = None
        self.confidence_threshold = 0.3

        # Load intents
        self.load_intents()

        # Train or load the model
        if os.path.exists('nlp_model.pkl'):
            self.load_model()
        else:
            self.train_model()

    def load_intents(self):
        """Load intents from JSON file"""
        try:
            with open('intents.json', 'r') as file:
                self.intents_data = json.load(file)
        except FileNotFoundError:
            print("Intents file not found. Creating basic intents...")
            self.create_basic_intents()

    def create_basic_intents(self):
        """Create basic intents if file doesn't exist"""
        basic_intents = {
            "intents": [
                {
                    "tag": "greeting",
                    "patterns": ["hi", "hello", "hey"],
                    "responses": ["Hello! How can I help you with your flight needs?"]
                },
                {
                    "tag": "flight_status",
                    "patterns": ["flight status", "check flight", "flight info"],
                    "responses": ["I can check flight status. What's the flight number?"]
                }
            ]
        }
        with open('intents.json', 'w') as file:
            json.dump(basic_intents, file, indent=2)
        self.intents_data = basic_intents

    def preprocess_text(self, text):
        """Clean and preprocess text"""
        # Convert to lowercase
        text = text.lower()

        # Remove special characters and digits
        text = re.sub(r'[^a-zA-Z\s]', '', text)

        # Tokenize
        words = nltk.word_tokenize(text)

        # Remove stop words and lemmatize
        words = [self.lemmatizer.lemmatize(word) for word in words
                 if word not in self.stop_words and len(word) > 2]

        return ' '.join(words)

    def prepare_training_data(self):
        """Prepare training data from intents"""
        patterns = []
        labels = []

        for intent in self.intents_data['intents']:
            tag = intent['tag']
            for pattern in intent['patterns']:
                processed_pattern = self.preprocess_text(pattern)
                patterns.append(processed_pattern)
                labels.append(tag)

        return patterns, labels

    def train_model(self):
        """Train the NLP model"""
        print("Training local NLP model...")

        # Prepare data
        patterns, labels = self.prepare_training_data()

        # Create pipeline
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=1000, ngram_range=(1, 2))),
            ('classifier', MultinomialNB(alpha=0.1))
        ])

        # Train the model
        self.pipeline.fit(patterns, labels)

        # Save the model
        self.save_model()

        print("NLP model trained and saved successfully!")

    def save_model(self):
        """Save the trained model"""
        with open('nlp_model.pkl', 'wb') as file:
            pickle.dump(self.pipeline, file)

    def load_model(self):
        """Load the trained model"""
        with open('nlp_model.pkl', 'rb') as file:
            self.pipeline = pickle.load(file)
        print("Local NLP model loaded successfully!")

    def predict_intent(self, text):
        """Predict intent from text"""
        if not self.pipeline:
            return None, 0.0

        processed_text = self.preprocess_text(text)

        try:
            # Get prediction probabilities
            probabilities = self.pipeline.predict_proba([processed_text])[0]
            classes = self.pipeline.classes_

            # Get the best prediction
            best_idx = np.argmax(probabilities)
            confidence = probabilities[best_idx]
            predicted_intent = classes[best_idx]

            # Check confidence threshold
            if confidence < self.confidence_threshold:
                return None, confidence

            return predicted_intent, confidence

        except Exception as e:
            print(f"Error in intent prediction: {e}")
            return None, 0.0

    def extract_entities(self, text):
        """Extract entities from text (flight numbers, airports, etc.)"""
        entities = {}

        # Flight number pattern (e.g., AA123, UA456)
        flight_pattern = r'\b[A-Z]{2}\d{1,4}\b'
        flights = re.findall(flight_pattern, text.upper())
        if flights:
            entities['flight_numbers'] = flights

        # Airport codes (3 letters)
        airport_pattern = r'\b[A-Z]{3}\b'
        airports = re.findall(airport_pattern, text.upper())
        # Filter out codes that are also common words
        common_codes = {'FOR', 'AND', 'THE', 'FROM'}
        if airports:
            entities['airport_codes'] = [code for code in airports if code not in common_codes]

        # Booking reference (alphanumeric)
        booking_pattern = r'\b[A-Z0-9]{6,8}\b'
        bookings = re.findall(booking_pattern, text.upper())
        if bookings:
            # Filter out flight numbers that were already matched
            existing_flights = set(entities.get('flight_numbers', []))
            entities['booking_refs'] = [b for b in bookings if b not in existing_flights]

        # --- START: NEW, SMARTER CITY/ROUTE PARSING ---
        lower_text = text.lower()
        if ' to ' in lower_text:
            # Handle "City to City" format
            parts = lower_text.split(' to ')
            # Clean up potential leading words like "flights from"
            departure_str = parts[0].replace('flights from', '').replace('flight from', '').strip()
            arrival_str = parts[1].strip()
            if departure_str and arrival_str:
                # Capitalize each word for consistency
                entities['cities'] = [' '.join(word.capitalize() for word in departure_str.split()),
                                      ' '.join(word.capitalize() for word in arrival_str.split())]
        else:
            # Fallback to original capitalized word matching for single cities
            city_pattern = r'\b[A-Z][a-z]{2,}(?: [A-Z][a-z]{2,})*\b'  # Handles multi-word names
            cities = re.findall(city_pattern, text)
            if cities:
                common_words = {'Flight', 'From', 'Book', 'Find', 'Check', 'When', 'What', 'Where', 'How'}
                cities = [city for city in cities if city not in common_words]
                if cities:
                    entities['cities'] = cities
        # --- END: NEW, SMARTER CITY/ROUTE PARSING ---

        return entities

    def fuzzy_match_intent(self, text, threshold=70):
        """Use fuzzy matching as fallback for intent recognition"""
        best_match = None
        best_score = 0

        for intent in self.intents_data['intents']:
            for pattern in intent['patterns']:
                score = fuzz.partial_ratio(text.lower(), pattern.lower())
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = intent['tag']

        return best_match, best_score / 100.0

    def get_response(self, intent_tag):
        """Get a response for the given intent"""
        for intent in self.intents_data['intents']:
            if intent['tag'] == intent_tag:
                return random.choice(intent['responses'])

        return "I'm not sure how to help with that. Could you please rephrase your question?"

    def process_message(self, message):
        """Process a message and return structured response"""
        # Extract entities first
        entities = self.extract_entities(message)

        # Predict intent
        intent, confidence = self.predict_intent(message)

        # Fallback to fuzzy matching if confidence is low
        if not intent or confidence < self.confidence_threshold:
            fuzzy_intent, fuzzy_confidence = self.fuzzy_match_intent(message)
            if fuzzy_intent and fuzzy_confidence > confidence:
                intent = fuzzy_intent
                confidence = fuzzy_confidence

        # Get response
        if intent:
            response = self.get_response(intent)
        else:
            response = "I'm not sure what you're looking for. I can help you with flight status, bookings, and flight searches. What do you need?"

        return {
            'response': response,
            'intent': intent,
            'confidence': confidence,
            'entities': entities
        }


# Context management for conversations
class ConversationContext:
    def __init__(self):
        self.user_contexts = {}  # Store context per user/session

    def get_context(self, session_id):
        """Get context for a specific session"""
        if session_id not in self.user_contexts:
            self.user_contexts[session_id] = {
                'previous_intent': None,
                'entities_history': [],
                'conversation_flow': [],
                'user_data': {}
            }
        return self.user_contexts[session_id]

    def update_context(self, session_id, intent, entities, user_message):
        """Update context with new information"""
        context = self.get_context(session_id)
        context['previous_intent'] = intent
        context['entities_history'].append(entities)
        context['conversation_flow'].append({
            'user_message': user_message,
            'intent': intent,
            'entities': entities
        })

        # Keep only last 10 interactions to manage memory
        if len(context['conversation_flow']) > 10:
            context['conversation_flow'] = context['conversation_flow'][-10:]
            context['entities_history'] = context['entities_history'][-10:]

    def clear_context(self, session_id):
        """Clear context for a session"""
        if session_id in self.user_contexts:
            del self.user_contexts[session_id]