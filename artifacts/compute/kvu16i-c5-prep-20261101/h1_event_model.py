#!/usr/bin/env python3
"""The historical row-4c H1 event *model*, derived from native response timings.

A previous no-draft request with >=3 predicted tokens arms the model; the first
following request with >128 newly processed prompt tokens is a modeled event.
This is a prediction, not direct evidence of a graph pin or HIP allocation.
"""

def classify(rows):
    pending = False
    out = []
    for row in rows:
        nodraft, prompt, predicted = row.get('nodraft'), row.get('prompt_n'), row.get('predicted_n')
        if type(nodraft) is not bool:
            raise ValueError('missing no-draft identity')
        if type(prompt) is not int or prompt < 0 or type(predicted) is not int or predicted < 0:
            raise ValueError('native prompt/predicted counters missing or invalid')
        event = pending and prompt > 128
        if event:
            pending = False
        out.append({**row, 'h1_event_model': event})
        if nodraft and predicted >= 3:
            pending = True
    return out
