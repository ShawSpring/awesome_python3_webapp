## 建立Page类来处理分页,可以在page_size更改每页项目的个数
import math
class Page(object):
    #根据 总项数,页面index,每页大小  得出offset,limit等  
    def __init__(self, item_count, page_index=1, page_size=10):
        self.item_count = item_count
        self.page_size = page_size
        # self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        self.page_count = math.ceil(item_count/page_size)
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_index < self.page_count
        self.has_previous = self.page_index > 1

    def __str__(self):
        return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)

    __repr__ = __str__

p = Page(100,1)
print(p.page_count)
p = Page(98,1)
print(p.page_count)
p = Page(90,1)
print(p.page_count)
print(p)