"""
Firebase Authentication Module for RoleSynch
Handles user sign-up, sign-in, sign-out, and session management
"""

import os
import json
import streamlit as st
import pyrebase
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime

# Load environment variables
load_dotenv()

# Firebase configuration for client-side auth (Pyrebase)
firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "databaseURL": ""  # Not needed for Firestore
}

# Initialize Pyrebase (for client-side authentication)
try:
    firebase = pyrebase.initialize_app(firebase_config)
    firebase_auth = firebase.auth()
except Exception as e:
    firebase_auth = None
    print(f"Warning: Could not initialize Firebase client: {e}")

# Initialize Firebase Admin SDK (for server-side operations)
# Supports both local file path and environment variable (for cloud deployment)
if not firebase_admin._apps:
    try:
        # First, try to load from environment variable (for Cloud Run)
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")

        if service_account_json:
            # Load from JSON string (Cloud Run / production)
            cred_dict = json.loads(service_account_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
        elif service_account_path and os.path.exists(service_account_path):
            # Load from file path (local development)
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
        else:
            db = None
            print("Warning: Firebase service account not configured")
    except Exception as e:
        db = None
        print(f"Warning: Could not initialize Firebase Admin: {e}")
else:
    db = firestore.client()


def initialize_session_state():
    """Initialize session state variables for authentication"""
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'analysis_count' not in st.session_state:
        st.session_state.analysis_count = 0
    if 'is_authenticated' not in st.session_state:
        st.session_state.is_authenticated = False
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False


def sign_up(email, password, display_name=None):
    """
    Create a new user account

    Args:
        email: User's email address
        password: User's password
        display_name: Optional display name

    Returns:
        tuple: (success: bool, message: str, user_data: dict or None)
    """
    try:
        if not firebase_auth:
            return False, "Firebase authentication not configured", None

        # Create user with Pyrebase
        user = firebase_auth.create_user_with_email_and_password(email, password)

        # Send email verification
        firebase_auth.send_email_verification(user['idToken'])

        # Create user document in Firestore
        if db:
            user_ref = db.collection('users').document(user['localId'])
            user_ref.set({
                'email': email,
                'display_name': display_name or email.split('@')[0],
                'created_at': datetime.now(),
                'analysis_count': 0,
                'is_premium': False,
                'is_admin': False,
                'free_trials_remaining': 3
            })

        return True, "Account created successfully! Please check your email to verify your account.", user

    except Exception as e:
        error_message = str(e)
        if "EMAIL_EXISTS" in error_message:
            return False, "An account with this email already exists", None
        elif "WEAK_PASSWORD" in error_message:
            return False, "Password should be at least 6 characters", None
        elif "INVALID_EMAIL" in error_message:
            return False, "Invalid email address", None
        else:
            return False, f"Error creating account: {error_message}", None


def sign_in(email, password):
    """
    Sign in an existing user

    Args:
        email: User's email address
        password: User's password

    Returns:
        tuple: (success: bool, message: str, user_data: dict or None)
    """
    try:
        if not firebase_auth:
            return False, "Firebase authentication not configured", None

        # Sign in with Pyrebase
        user = firebase_auth.sign_in_with_email_and_password(email, password)

        # Get user data from Firestore
        user_data = None
        if db:
            user_ref = db.collection('users').document(user['localId'])
            user_doc = user_ref.get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_data['user_id'] = user['localId']

        # Update session state
        st.session_state.user = user
        st.session_state.user_id = user['localId']
        st.session_state.user_email = email
        st.session_state.is_authenticated = True
        if user_data:
            st.session_state.analysis_count = user_data.get('analysis_count', 0)
            st.session_state.free_trials_remaining = user_data.get('free_trials_remaining', 3)
            st.session_state.is_admin = user_data.get('is_admin', False)

        return True, "Successfully signed in!", user_data

    except Exception as e:
        error_message = str(e)
        if "INVALID_LOGIN_CREDENTIALS" in error_message or "INVALID_PASSWORD" in error_message:
            return False, "Invalid email or password", None
        elif "EMAIL_NOT_FOUND" in error_message:
            return False, "No account found with this email", None
        elif "USER_DISABLED" in error_message:
            return False, "This account has been disabled", None
        else:
            return False, f"Error signing in: {error_message}", None


def sign_out():
    """Sign out the current user and clear session state"""
    st.session_state.user = None
    st.session_state.user_id = None
    st.session_state.user_email = None
    st.session_state.is_authenticated = False
    st.session_state.analysis_count = 0
    st.session_state.free_trials_remaining = 3
    st.session_state.is_admin = False


def is_authenticated():
    """Check if a user is currently authenticated"""
    return st.session_state.get('is_authenticated', False)


def get_current_user():
    """Get the currently authenticated user's data"""
    if not is_authenticated():
        return None

    return {
        'user_id': st.session_state.get('user_id'),
        'email': st.session_state.get('user_email'),
        'analysis_count': st.session_state.get('analysis_count', 0),
        'free_trials_remaining': st.session_state.get('free_trials_remaining', 3),
        'is_admin': st.session_state.get('is_admin', False)
    }


def can_perform_analysis():
    """
    Check if the current user can perform an analysis

    Returns:
        tuple: (can_analyze: bool, message: str)
    """
    user = get_current_user()
    if not user:
        return False, "Please sign in to perform an analysis"

    # Admins have unlimited analyses
    if user.get('is_admin', False):
        return True, "Admin: Unlimited analyses"

    free_trials = user.get('free_trials_remaining', 0)

    if free_trials > 0:
        return True, f"You have {free_trials} free analyses remaining"
    else:
        return False, "You have used all your free analyses. Please upgrade to continue."


def increment_analysis_count():
    """Increment the analysis count for the current user"""
    if not is_authenticated():
        return False

    try:
        user_id = st.session_state.user_id
        if db:
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                current_count = user_data.get('analysis_count', 0)
                free_trials = user_data.get('free_trials_remaining', 3)
                is_admin = user_data.get('is_admin', False)

                # Update Firestore - admins don't lose free trials
                update_data = {
                    'analysis_count': current_count + 1,
                    'last_analysis': datetime.now()
                }

                if not is_admin:
                    update_data['free_trials_remaining'] = max(0, free_trials - 1)

                user_ref.update(update_data)

                # Update session state
                st.session_state.analysis_count = current_count + 1
                if not is_admin:
                    st.session_state.free_trials_remaining = max(0, free_trials - 1)

                return True
        return False

    except Exception as e:
        print(f"Error incrementing analysis count: {e}")
        return False


def get_user_profile(user_id=None):
    """
    Get user profile data from Firestore

    Args:
        user_id: User ID (defaults to current user)

    Returns:
        dict: User profile data or None
    """
    if not user_id:
        user_id = st.session_state.get('user_id')

    if not user_id or not db:
        return None

    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if user_doc.exists:
            return user_doc.to_dict()
        return None

    except Exception as e:
        print(f"Error getting user profile: {e}")
        return None
