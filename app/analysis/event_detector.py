"""
Violence Event Detector.
Merges temporal violations across modalities into unified events.
Handles overlap merging (e.g., video punch at 5-10s + audio scream at 6-8s = single event).
"""
from typing import Dict, Any, List

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ViolenceEventDetector:
    """Merges per-modality violations into unified violence events."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def detect_events(self, violations: List[Dict[str, Any]], merge_gap: float = 2.0) -> List[Dict[str, Any]]:
        """
        Merge violations across modalities into unified events.

        Args:
            violations: List of violations from all modalities
            merge_gap: Maximum gap (seconds) between violations to merge

        Returns:
            List of merged violence events
        """
        if not violations:
            return []

        # Separate text violations (sentence-based) from temporal ones
        temporal_violations = []
        text_violations = []

        for v in violations:
            if v.get('modality') == 'text':
                text_violations.append(v)
            elif 'start_seconds' in v:
                temporal_violations.append(v)

        # Sort temporal violations by start time
        temporal_violations.sort(key=lambda v: v.get('start_seconds', 0))

        # Merge overlapping/adjacent temporal violations
        events = []
        if temporal_violations:
            current_event = self._init_event(temporal_violations[0])

            for v in temporal_violations[1:]:
                v_start = v.get('start_seconds', 0)
                event_end = current_event['end_seconds']

                if v_start <= event_end + merge_gap:
                    # Merge into current event
                    current_event = self._merge_into_event(current_event, v)
                else:
                    # Save current event, start new one
                    events.append(self._finalize_event(current_event))
                    current_event = self._init_event(v)

            events.append(self._finalize_event(current_event))

        # Add text violations as separate events
        for tv in text_violations:
            events.append({
                'event_id': len(events) + 1,
                'type': 'text_violation',
                'modalities': ['text'],
                'start_seconds': None,
                'end_seconds': None,
                'start_time': None,
                'end_time': None,
                'severity': tv.get('confidence', 0),
                'reasons': [tv.get('reason', tv.get('sentence', ''))],
                'violation_count': 1,
            })

        # Assign sequential event IDs
        for i, event in enumerate(events, 1):
            event['event_id'] = i

        logger.info(f"Detected {len(events)} violence events from {len(violations)} violations")
        return events

    def _init_event(self, violation: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize a new event from a violation."""
        return {
            'start_seconds': violation.get('start_seconds', 0),
            'end_seconds': violation.get('end_seconds', violation.get('start_seconds', 0) + 1),
            'start_time': violation.get('start_time', '0:00'),
            'end_time': violation.get('end_time', '0:01'),
            'modalities': {violation.get('modality', 'unknown')},
            'reasons': [violation.get('reason', '')],
            'max_confidence': violation.get('confidence', 0),
            'violation_count': 1,
        }

    def _merge_into_event(self, event: Dict[str, Any], violation: Dict[str, Any]) -> Dict[str, Any]:
        """Merge a violation into an existing event."""
        v_end = violation.get('end_seconds', violation.get('start_seconds', 0) + 1)

        if v_end > event['end_seconds']:
            event['end_seconds'] = v_end
            event['end_time'] = violation.get('end_time', event['end_time'])

        event['modalities'].add(violation.get('modality', 'unknown'))
        event['reasons'].append(violation.get('reason', ''))
        event['max_confidence'] = max(event['max_confidence'], violation.get('confidence', 0))
        event['violation_count'] += 1
        return event

    def _finalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize an event for output."""
        return {
            'event_id': 0,  # Will be set later
            'type': 'temporal_violation',
            'modalities': sorted(event['modalities']),
            'start_seconds': event['start_seconds'],
            'end_seconds': event['end_seconds'],
            'start_time': event['start_time'],
            'end_time': event['end_time'],
            'severity': event['max_confidence'],
            'reasons': [r for r in event['reasons'] if r][:5],
            'violation_count': event['violation_count'],
            'multi_modal': len(event['modalities']) > 1,
        }


_event_detector = None


def get_event_detector() -> ViolenceEventDetector:
    global _event_detector
    if _event_detector is None:
        _event_detector = ViolenceEventDetector()
    return _event_detector
