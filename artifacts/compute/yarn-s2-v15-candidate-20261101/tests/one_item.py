"""Fail-closed one-native-item budget for a single resumed S2 worker process."""

class OneItemBudget:
    def __init__(self):
        self._selected = None
        self._claimed = False

    def first_pending(self, items):
        if self._selected is not None:
            raise RuntimeError('initial pending selection already consumed')
        items = list(items)
        if not items:
            return []
        item_id = items[0].get('item_id')
        if not isinstance(item_id, str) or not item_id:
            raise ValueError('selected item identity missing')
        self._selected = item_id
        return items[:1]

    def claim(self, item_id):
        if not self._selected or item_id != self._selected or self._claimed:
            raise RuntimeError('one-item exposure budget refused')
        self._claimed = True
