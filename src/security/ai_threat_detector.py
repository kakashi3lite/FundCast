"""
Advanced AI Threat Detection System
Multi-layered detection for prompt injection, adversarial inputs, and AI-powered attacks
"""

import asyncio
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ..ai_inference.models import get_model_manager
from ..database import get_database
from ..config import settings


class ThreatLevel(Enum):
    """Threat severity levels"""
    BENIGN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    BLOCK = 5


class AttackType(Enum):
    """Types of AI attacks detected"""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAKING = "jailbreaking" 
    ADVERSARIAL_INPUT = "adversarial_input"
    SOCIAL_ENGINEERING = "social_engineering"
    MODEL_EXTRACTION = "model_extraction"
    DATA_POISONING = "data_poisoning"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    UNKNOWN = "unknown"


@dataclass
class ThreatAssessment:
    """Comprehensive threat assessment result"""
    threat_level: ThreatLevel
    attack_type: AttackType
    confidence: float
    risk_score: float
    detected_patterns: List[str]
    mitigation_actions: List[str]
    evidence: Dict[str, Any]
    timestamp: datetime


class PromptInjectionDetector:
    """Advanced prompt injection detection using multiple techniques"""
    
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.attack_patterns = self._load_attack_patterns()
        self.semantic_threshold = 0.8
        self.context_window_size = 2048
        
    async def initialize(self):
        """Initialize ML models for detection"""
        try:
            # Load pre-trained transformer model for injection detection
            model_name = "microsoft/DialoGPT-medium"  # Lightweight option
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            self.model.eval()
        except Exception as e:
            # Fallback to pattern-based detection only
            print(f"Warning: Could not load transformer model: {e}")
    
    def _load_attack_patterns(self) -> List[Dict[str, Any]]:
        """Load known prompt injection attack patterns"""
        return [
            {
                "name": "direct_instruction_override",
                "pattern": r"(?i)(ignore|forget|disregard|override)\s+(previous|all|above|prior)\s+(instructions?|prompts?|rules?)",
                "severity": ThreatLevel.HIGH,
                "description": "Direct instruction override attempt"
            },
            {
                "name": "role_hijacking", 
                "pattern": r"(?i)(you\s+are\s+now|pretend\s+to\s+be|act\s+as|roleplay\s+as)\s+(admin|developer|system|jailbreak)",
                "severity": ThreatLevel.CRITICAL,
                "description": "Role hijacking attempt"
            },
            {
                "name": "system_prompt_extraction",
                "pattern": r"(?i)(show|print|display|reveal|tell\s+me)\s+(your|the)\s+(system\s+prompt|initial\s+prompt|instructions)",
                "severity": ThreatLevel.HIGH,
                "description": "System prompt extraction attempt"
            },
            {
                "name": "jailbreak_keywords",
                "pattern": r"(?i)(jailbreak|dan\s+mode|do\s+anything\s+now|unrestricted|bypass\s+safety)",
                "severity": ThreatLevel.CRITICAL,
                "description": "Known jailbreaking keywords"
            },
            {
                "name": "prompt_injection_markers",
                "pattern": r"(?i)(\\n\\n|###\s+|---\s+|end\s+of\s+prompt|new\s+instructions?)",
                "severity": ThreatLevel.MEDIUM,
                "description": "Prompt structure manipulation markers"
            },
            {
                "name": "encoding_obfuscation",
                "pattern": r"(\\x[0-9a-f]{2}|\\u[0-9a-f]{4}|%[0-9a-f]{2}|&[a-z]+;)",
                "severity": ThreatLevel.MEDIUM,
                "description": "Encoding-based obfuscation"
            },
            {
                "name": "multi_language_bypass",
                "pattern": r"[\u4e00-\u9fff\u0400-\u04ff\u0600-\u06ff\u0590-\u05ff].*(?i)(system|admin|ignore|bypass)",
                "severity": ThreatLevel.HIGH,
                "description": "Multi-language bypass attempt"
            }
        ]
    
    async def detect_injection(self, prompt: str, context: Optional[Dict] = None) -> Tuple[ThreatLevel, List[str], float]:
        """Comprehensive prompt injection detection"""
        
        detected_patterns = []
        max_severity = ThreatLevel.BENIGN
        confidence_scores = []
        
        # Stage 1: Pattern-based detection
        pattern_results = await self._pattern_based_detection(prompt)
        for result in pattern_results:
            detected_patterns.append(result["name"])
            if result["severity"].value > max_severity.value:
                max_severity = result["severity"]
            confidence_scores.append(0.9)  # High confidence for pattern matches
        
        # Stage 2: Semantic analysis (if model available)
        if self.model is not None:
            semantic_result = await self._semantic_analysis(prompt, context)
            if semantic_result["threat_detected"]:
                detected_patterns.append("semantic_anomaly")
                if semantic_result["severity"].value > max_severity.value:
                    max_severity = semantic_result["severity"]
                confidence_scores.append(semantic_result["confidence"])
        
        # Stage 3: Context manipulation detection
        context_result = await self._detect_context_manipulation(prompt, context)
        if context_result["threat_detected"]:
            detected_patterns.append("context_manipulation")
            if context_result["severity"].value > max_severity.value:
                max_severity = context_result["severity"]
            confidence_scores.append(context_result["confidence"])
        
        # Stage 4: Instruction hierarchy analysis
        hierarchy_result = await self._analyze_instruction_hierarchy(prompt)
        if hierarchy_result["threat_detected"]:
            detected_patterns.append("instruction_hierarchy_bypass")
            if hierarchy_result["severity"].value > max_severity.value:
                max_severity = hierarchy_result["severity"]
            confidence_scores.append(hierarchy_result["confidence"])
        
        # Calculate overall confidence
        overall_confidence = np.mean(confidence_scores) if confidence_scores else 0.0
        
        return max_severity, detected_patterns, overall_confidence
    
    async def _pattern_based_detection(self, prompt: str) -> List[Dict[str, Any]]:
        """Pattern-based injection detection"""
        results = []
        
        for pattern_info in self.attack_patterns:
            matches = re.finditer(pattern_info["pattern"], prompt)
            for match in matches:
                results.append({
                    "name": pattern_info["name"],
                    "severity": pattern_info["severity"],
                    "description": pattern_info["description"],
                    "match": match.group(),
                    "position": match.span()
                })
        
        return results
    
    async def _semantic_analysis(self, prompt: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Semantic analysis for obfuscated injections"""
        if not self.model:
            return {"threat_detected": False, "confidence": 0.0}
        
        try:
            # Tokenize and encode prompt
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state.mean(dim=1).numpy()
            
            # Analyze semantic similarity to known attack vectors
            # This would use pre-computed embeddings of known attacks
            similarity_score = self._compute_attack_similarity(embeddings)
            
            threat_detected = similarity_score > self.semantic_threshold
            severity = ThreatLevel.HIGH if similarity_score > 0.9 else ThreatLevel.MEDIUM
            
            return {
                "threat_detected": threat_detected,
                "severity": severity,
                "confidence": float(similarity_score),
                "similarity_score": float(similarity_score)
            }
            
        except Exception as e:
            print(f"Semantic analysis error: {e}")
            return {"threat_detected": False, "confidence": 0.0}
    
    def _compute_attack_similarity(self, embeddings: np.ndarray) -> float:
        """Compute similarity to known attack embeddings"""
        # This would use a database of pre-computed attack embeddings
        # For now, return a mock similarity based on embedding characteristics
        
        # Simple heuristic: look for unusual patterns in embedding space
        embedding_variance = np.var(embeddings)
        embedding_mean = np.mean(np.abs(embeddings))
        
        # High variance + high magnitude often indicates adversarial content
        anomaly_score = min(1.0, (embedding_variance * embedding_mean) / 10.0)
        return anomaly_score
    
    async def _detect_context_manipulation(self, prompt: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Detect context window manipulation attempts"""
        
        # Check for context overflow attempts
        if len(prompt) > self.context_window_size * 0.8:
            return {
                "threat_detected": True,
                "severity": ThreatLevel.MEDIUM,
                "confidence": 0.8,
                "reason": "Context window overflow attempt"
            }
        
        # Check for rapid context switching
        context_switches = self._count_context_switches(prompt)
        if context_switches > 10:
            return {
                "threat_detected": True,
                "severity": ThreatLevel.MEDIUM,
                "confidence": 0.7,
                "reason": f"Excessive context switching ({context_switches})"
            }
        
        return {"threat_detected": False, "confidence": 0.0}
    
    def _count_context_switches(self, prompt: str) -> int:
        """Count context switching markers in prompt"""
        switch_markers = [
            r"(?i)now\s+let's",
            r"(?i)switching\s+to",
            r"(?i)new\s+topic",
            r"(?i)different\s+subject",
            r"---+",
            r"###+"
        ]
        
        total_switches = 0
        for marker in switch_markers:
            total_switches += len(re.findall(marker, prompt))
        
        return total_switches
    
    async def _analyze_instruction_hierarchy(self, prompt: str) -> Dict[str, Any]:
        """Analyze instruction hierarchy bypass attempts"""
        
        # Look for instruction prioritization attempts
        priority_patterns = [
            r"(?i)most\s+important",
            r"(?i)highest\s+priority",
            r"(?i)override\s+all",
            r"(?i)primary\s+directive",
            r"(?i)super\s+admin"
        ]
        
        hierarchy_violations = 0
        for pattern in priority_patterns:
            hierarchy_violations += len(re.findall(pattern, prompt))
        
        if hierarchy_violations > 0:
            return {
                "threat_detected": True,
                "severity": ThreatLevel.HIGH,
                "confidence": 0.85,
                "violations": hierarchy_violations
            }
        
        return {"threat_detected": False, "confidence": 0.0}


class BehavioralAnomalyDetector:
    """Detect behavioral anomalies indicating AI-powered attacks"""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.baseline_features = {}
        
    async def analyze_behavior(self, user_id: str, session_data: Dict) -> Dict[str, Any]:
        """Analyze user behavior for anomalies"""
        
        # Extract behavioral features
        features = await self._extract_behavioral_features(session_data)
        
        # Get user baseline if available
        baseline = await self._get_user_baseline(user_id)
        
        # Calculate anomaly scores
        anomaly_score = await self._calculate_anomaly_score(features, baseline)
        
        # Detect specific attack patterns
        attack_indicators = await self._detect_attack_indicators(session_data)
        
        return {
            "anomaly_score": anomaly_score,
            "attack_indicators": attack_indicators,
            "behavioral_features": features,
            "baseline_available": baseline is not None,
            "threat_level": self._calculate_threat_level(anomaly_score, attack_indicators)
        }
    
    async def _extract_behavioral_features(self, session_data: Dict) -> Dict[str, float]:
        """Extract behavioral features for analysis"""
        
        features = {}
        
        # Timing features
        features["avg_request_interval"] = self._calculate_avg_interval(session_data.get("timestamps", []))
        features["request_frequency"] = len(session_data.get("requests", []))
        features["session_duration"] = self._calculate_session_duration(session_data)
        
        # Interaction features
        features["avg_input_length"] = self._calculate_avg_input_length(session_data)
        features["unique_endpoints"] = len(set(session_data.get("endpoints", [])))
        features["error_rate"] = self._calculate_error_rate(session_data)
        
        # Content features
        features["prompt_complexity"] = self._calculate_prompt_complexity(session_data)
        features["vocabulary_diversity"] = self._calculate_vocabulary_diversity(session_data)
        features["sentiment_variance"] = self._calculate_sentiment_variance(session_data)
        
        # Automation indicators
        features["perfect_timing_ratio"] = self._calculate_perfect_timing_ratio(session_data)
        features["repetitive_pattern_score"] = self._calculate_repetitive_patterns(session_data)
        features["human_typo_score"] = self._calculate_human_typo_score(session_data)
        
        return features
    
    def _calculate_avg_interval(self, timestamps: List[datetime]) -> float:
        """Calculate average time between requests"""
        if len(timestamps) < 2:
            return 0.0
        
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        return np.mean(intervals)
    
    def _calculate_session_duration(self, session_data: Dict) -> float:
        """Calculate total session duration"""
        timestamps = session_data.get("timestamps", [])
        if len(timestamps) < 2:
            return 0.0
        
        return (timestamps[-1] - timestamps[0]).total_seconds()
    
    def _calculate_avg_input_length(self, session_data: Dict) -> float:
        """Calculate average input length"""
        inputs = session_data.get("inputs", [])
        if not inputs:
            return 0.0
        
        lengths = [len(str(inp)) for inp in inputs]
        return np.mean(lengths)
    
    def _calculate_error_rate(self, session_data: Dict) -> float:
        """Calculate error rate in requests"""
        responses = session_data.get("responses", [])
        if not responses:
            return 0.0
        
        errors = sum(1 for resp in responses if resp.get("status_code", 200) >= 400)
        return errors / len(responses)
    
    def _calculate_prompt_complexity(self, session_data: Dict) -> float:
        """Calculate average prompt complexity score"""
        inputs = session_data.get("inputs", [])
        if not inputs:
            return 0.0
        
        complexity_scores = []
        for inp in inputs:
            text = str(inp)
            # Simple complexity metrics
            word_count = len(text.split())
            unique_words = len(set(text.lower().split()))
            avg_word_length = np.mean([len(word) for word in text.split()])
            
            # Complexity score based on vocabulary richness and word length
            complexity = (unique_words / max(word_count, 1)) * avg_word_length
            complexity_scores.append(complexity)
        
        return np.mean(complexity_scores)
    
    def _calculate_vocabulary_diversity(self, session_data: Dict) -> float:
        """Calculate vocabulary diversity across inputs"""
        inputs = session_data.get("inputs", [])
        if not inputs:
            return 0.0
        
        all_words = []
        for inp in inputs:
            words = str(inp).lower().split()
            all_words.extend(words)
        
        if not all_words:
            return 0.0
        
        # Type-token ratio as diversity measure
        unique_words = len(set(all_words))
        total_words = len(all_words)
        
        return unique_words / total_words
    
    def _calculate_sentiment_variance(self, session_data: Dict) -> float:
        """Calculate sentiment variance across inputs"""
        # This would use a sentiment analysis model
        # For now, return a mock variance based on punctuation and capitalization
        inputs = session_data.get("inputs", [])
        if not inputs:
            return 0.0
        
        sentiment_scores = []
        for inp in inputs:
            text = str(inp)
            # Simple sentiment proxy
            exclamation_ratio = text.count('!') / max(len(text), 1)
            caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
            question_ratio = text.count('?') / max(len(text), 1)
            
            sentiment_proxy = (exclamation_ratio * 2) + caps_ratio + question_ratio
            sentiment_scores.append(sentiment_proxy)
        
        return float(np.var(sentiment_scores)) if sentiment_scores else 0.0
    
    def _calculate_perfect_timing_ratio(self, session_data: Dict) -> float:
        """Calculate ratio of perfectly timed requests (automation indicator)"""
        timestamps = session_data.get("timestamps", [])
        if len(timestamps) < 3:
            return 0.0
        
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        # Count intervals that are suspiciously consistent (within 100ms)
        consistent_intervals = sum(1 for interval in intervals if interval > 0 and interval == round(interval, 1))
        
        return consistent_intervals / len(intervals)
    
    def _calculate_repetitive_patterns(self, session_data: Dict) -> float:
        """Calculate score for repetitive patterns (automation indicator)"""
        inputs = session_data.get("inputs", [])
        if len(inputs) < 2:
            return 0.0
        
        repetitive_score = 0.0
        for i in range(1, len(inputs)):
            current = str(inputs[i]).lower().strip()
            previous = str(inputs[i-1]).lower().strip()
            
            # Calculate similarity
            if current == previous:
                repetitive_score += 1.0
            else:
                # Levenshtein distance approximation
                common_chars = len(set(current) & set(previous))
                max_chars = max(len(current), len(previous))
                similarity = common_chars / max(max_chars, 1)
                if similarity > 0.8:
                    repetitive_score += similarity
        
        return repetitive_score / (len(inputs) - 1)
    
    def _calculate_human_typo_score(self, session_data: Dict) -> float:
        """Calculate score for human-like typos and imperfections"""
        inputs = session_data.get("inputs", [])
        if not inputs:
            return 0.0
        
        human_indicators = 0
        total_chars = 0
        
        for inp in inputs:
            text = str(inp)
            total_chars += len(text)
            
            # Look for human indicators
            # Double letters (common typos)
            human_indicators += len(re.findall(r'([a-z])\1{2,}', text.lower()))
            
            # Common typos
            human_indicators += len(re.findall(r'teh|adn|hte|thier|recieve', text.lower()))
            
            # Inconsistent punctuation
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                if sentence.strip() and not sentence.strip()[0].isupper():
                    human_indicators += 1
        
        return human_indicators / max(total_chars / 100, 1)  # Normalize per 100 chars
    
    async def _get_user_baseline(self, user_id: str) -> Optional[Dict]:
        """Get user behavioral baseline from database"""
        # This would query the database for user's historical behavior
        # For now, return None (no baseline available)
        return None
    
    async def _calculate_anomaly_score(self, features: Dict[str, float], baseline: Optional[Dict]) -> float:
        """Calculate behavioral anomaly score"""
        if baseline is None:
            # Without baseline, use isolation forest on current features
            feature_vector = np.array(list(features.values())).reshape(1, -1)
            
            if not self.is_trained:
                # Use current features as baseline (first session)
                return 0.0
            
            # Normalize features
            normalized_features = self.scaler.transform(feature_vector)
            
            # Get anomaly score
            anomaly_score = self.isolation_forest.decision_function(normalized_features)[0]
            
            # Convert to 0-1 range (higher = more anomalous)
            return max(0.0, 1.0 - anomaly_score)
        
        else:
            # Compare with user baseline
            baseline_features = baseline.get("features", {})
            anomaly_score = 0.0
            
            for feature, value in features.items():
                if feature in baseline_features:
                    baseline_value = baseline_features[feature]
                    baseline_std = baseline.get("std", {}).get(feature, 1.0)
                    
                    # Z-score based anomaly
                    z_score = abs(value - baseline_value) / max(baseline_std, 0.1)
                    anomaly_score += min(z_score / 3.0, 1.0)  # Cap at 1.0
            
            return anomaly_score / len(features)
    
    async def _detect_attack_indicators(self, session_data: Dict) -> List[str]:
        """Detect specific attack indicators"""
        indicators = []
        
        # High-frequency requests (potential DoS)
        if len(session_data.get("requests", [])) > 100:
            indicators.append("high_frequency_requests")
        
        # Unusual error patterns
        if self._calculate_error_rate(session_data) > 0.5:
            indicators.append("high_error_rate")
        
        # Automation patterns
        if self._calculate_perfect_timing_ratio(session_data) > 0.8:
            indicators.append("automation_detected")
        
        # Repetitive patterns
        if self._calculate_repetitive_patterns(session_data) > 0.7:
            indicators.append("repetitive_patterns")
        
        # Lack of human indicators
        if self._calculate_human_typo_score(session_data) < 0.01:
            indicators.append("no_human_indicators")
        
        return indicators
    
    def _calculate_threat_level(self, anomaly_score: float, attack_indicators: List[str]) -> ThreatLevel:
        """Calculate overall threat level"""
        base_threat = ThreatLevel.BENIGN
        
        # Anomaly score contribution
        if anomaly_score > 0.8:
            base_threat = ThreatLevel.HIGH
        elif anomaly_score > 0.6:
            base_threat = ThreatLevel.MEDIUM
        elif anomaly_score > 0.4:
            base_threat = ThreatLevel.LOW
        
        # Attack indicators contribution
        if len(attack_indicators) >= 3:
            return ThreatLevel.CRITICAL
        elif len(attack_indicators) >= 2:
            return max(base_threat, ThreatLevel.HIGH)
        elif len(attack_indicators) >= 1:
            return max(base_threat, ThreatLevel.MEDIUM)
        
        return base_threat


class AIThreatDetector:
    """Main AI threat detection coordinator"""
    
    def __init__(self):
        self.prompt_detector = PromptInjectionDetector()
        self.behavioral_detector = BehavioralAnomalyDetector()
        self.threat_cache = {}
        self.cache_ttl = timedelta(minutes=5)
        
    async def initialize(self):
        """Initialize all detection components"""
        await self.prompt_detector.initialize()
        
    async def analyze_request(self, request_data: Dict[str, Any]) -> ThreatAssessment:
        """Comprehensive threat analysis of request"""
        
        # Extract key components
        user_id = request_data.get("user_id")
        prompt = request_data.get("query", request_data.get("prompt", ""))
        context = request_data.get("context", {})
        session_data = request_data.get("session_data", {})
        
        # Check cache first
        cache_key = self._generate_cache_key(request_data)
        if cache_key in self.threat_cache:
            cached_result, timestamp = self.threat_cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return cached_result
        
        # Multi-layer analysis
        analyses = await asyncio.gather(
            self._analyze_prompt_injection(prompt, context),
            self._analyze_behavioral_patterns(user_id, session_data),
            self._analyze_content_anomalies(request_data),
            return_exceptions=True
        )
        
        # Process analysis results
        threat_level = ThreatLevel.BENIGN
        detected_patterns = []
        evidence = {}
        attack_type = AttackType.UNKNOWN
        confidence_scores = []
        
        # Prompt injection analysis
        if not isinstance(analyses[0], Exception):
            prompt_threat, prompt_patterns, prompt_confidence = analyses[0]
            if prompt_threat.value > threat_level.value:
                threat_level = prompt_threat
                attack_type = AttackType.PROMPT_INJECTION
            detected_patterns.extend(prompt_patterns)
            confidence_scores.append(prompt_confidence)
            evidence["prompt_analysis"] = {
                "threat_level": prompt_threat.name,
                "patterns": prompt_patterns,
                "confidence": prompt_confidence
            }
        
        # Behavioral analysis
        if not isinstance(analyses[1], Exception):
            behavioral_result = analyses[1]
            behavioral_threat = behavioral_result["threat_level"]
            if behavioral_threat.value > threat_level.value:
                threat_level = behavioral_threat
                attack_type = AttackType.BEHAVIORAL_ANOMALY
            detected_patterns.extend(behavioral_result["attack_indicators"])
            confidence_scores.append(behavioral_result["anomaly_score"])
            evidence["behavioral_analysis"] = behavioral_result
        
        # Content anomaly analysis
        if not isinstance(analyses[2], Exception):
            content_result = analyses[2]
            if content_result["threat_detected"]:
                content_threat = content_result["threat_level"]
                if content_threat.value > threat_level.value:
                    threat_level = content_threat
                detected_patterns.append("content_anomaly")
                confidence_scores.append(content_result["confidence"])
                evidence["content_analysis"] = content_result
        
        # Calculate aggregate scores
        overall_confidence = np.mean(confidence_scores) if confidence_scores else 0.0
        risk_score = self._calculate_risk_score(threat_level, overall_confidence, detected_patterns)
        
        # Generate mitigation actions
        mitigation_actions = self._generate_mitigation_actions(threat_level, detected_patterns)
        
        # Create assessment
        assessment = ThreatAssessment(
            threat_level=threat_level,
            attack_type=attack_type,
            confidence=overall_confidence,
            risk_score=risk_score,
            detected_patterns=detected_patterns,
            mitigation_actions=mitigation_actions,
            evidence=evidence,
            timestamp=datetime.now()
        )
        
        # Cache result
        self.threat_cache[cache_key] = (assessment, datetime.now())
        
        return assessment
    
    async def _analyze_prompt_injection(self, prompt: str, context: Dict) -> Tuple[ThreatLevel, List[str], float]:
        """Analyze prompt for injection attacks"""
        if not prompt.strip():
            return ThreatLevel.BENIGN, [], 0.0
        
        return await self.prompt_detector.detect_injection(prompt, context)
    
    async def _analyze_behavioral_patterns(self, user_id: Optional[str], session_data: Dict) -> Dict[str, Any]:
        """Analyze behavioral patterns for anomalies"""
        if not user_id or not session_data:
            return {
                "anomaly_score": 0.0,
                "attack_indicators": [],
                "threat_level": ThreatLevel.BENIGN
            }
        
        return await self.behavioral_detector.analyze_behavior(user_id, session_data)
    
    async def _analyze_content_anomalies(self, request_data: Dict) -> Dict[str, Any]:
        """Analyze request content for anomalies"""
        
        anomalies = []
        threat_detected = False
        confidence = 0.0
        
        # Check request size
        request_size = len(json.dumps(request_data))
        if request_size > 100 * 1024:  # 100KB threshold
            anomalies.append("oversized_request")
            threat_detected = True
            confidence = 0.8
        
        # Check for suspicious headers or metadata
        headers = request_data.get("headers", {})
        if any(header.lower().startswith("x-forwarded") for header in headers):
            proxy_count = sum(1 for header in headers if header.lower().startswith("x-forwarded"))
            if proxy_count > 5:
                anomalies.append("proxy_chain_abuse")
                threat_detected = True
                confidence = max(confidence, 0.7)
        
        # Check for encoded payloads
        content = str(request_data)
        if re.search(r'(\\x[0-9a-f]{2}|\\u[0-9a-f]{4}|%[0-9a-f]{2})', content):
            anomalies.append("encoded_payload")
            threat_detected = True
            confidence = max(confidence, 0.6)
        
        return {
            "threat_detected": threat_detected,
            "threat_level": ThreatLevel.MEDIUM if threat_detected else ThreatLevel.BENIGN,
            "anomalies": anomalies,
            "confidence": confidence
        }
    
    def _generate_cache_key(self, request_data: Dict) -> str:
        """Generate cache key for request"""
        # Create hash of relevant request components
        key_data = {
            "user_id": request_data.get("user_id"),
            "query_hash": hashlib.md5(str(request_data.get("query", "")).encode()).hexdigest(),
            "endpoint": request_data.get("endpoint")
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def _calculate_risk_score(self, threat_level: ThreatLevel, confidence: float, patterns: List[str]) -> float:
        """Calculate overall risk score"""
        base_risk = threat_level.value / 5.0  # Normalize to 0-1
        confidence_weight = confidence
        pattern_weight = min(len(patterns) / 10.0, 1.0)  # Cap at 1.0
        
        return (base_risk * 0.5) + (confidence_weight * 0.3) + (pattern_weight * 0.2)
    
    def _generate_mitigation_actions(self, threat_level: ThreatLevel, patterns: List[str]) -> List[str]:
        """Generate recommended mitigation actions"""
        actions = []
        
        if threat_level >= ThreatLevel.CRITICAL:
            actions.extend([
                "block_request",
                "alert_security_team",
                "isolate_user_session",
                "preserve_evidence"
            ])
        elif threat_level >= ThreatLevel.HIGH:
            actions.extend([
                "challenge_user",
                "rate_limit_user",
                "log_detailed_event",
                "monitor_user_activity"
            ])
        elif threat_level >= ThreatLevel.MEDIUM:
            actions.extend([
                "log_security_event",
                "increase_monitoring",
                "apply_content_filter"
            ])
        elif threat_level >= ThreatLevel.LOW:
            actions.extend([
                "log_event",
                "passive_monitoring"
            ])
        
        # Pattern-specific actions
        if "prompt_injection" in patterns:
            actions.append("sanitize_prompt")
        if "automation_detected" in patterns:
            actions.append("require_captcha")
        if "behavioral_anomaly" in patterns:
            actions.append("verify_identity")
        
        return list(set(actions))  # Remove duplicates