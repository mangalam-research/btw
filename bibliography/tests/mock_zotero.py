import copy


class Records(object):

    def __init__(self, values):
        self._initial_values = values
        self.reset()

    def get_item(self, itemKey):
        return [x for x in self.values if x["data"]["itemKey"] == itemKey][0]

    def __len__(self):
        return len(self.values)

    def reset(self):
        self.values = copy.deepcopy(self._initial_values)
