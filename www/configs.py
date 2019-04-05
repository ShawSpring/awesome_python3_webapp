import configs_default
#import configs_override  #不一定有这个文件 得换成 try except 
configs = configs_default.configs

def chain(*dicts): #自己实现一个dict版本的chain
    for d in dicts:
        for k,v in d.items():
            yield (k,v)

def merge_configs(c1,c2):
    results={}
    for k,v in chain(c1,c2):
        if k in results:
            results[k] = merge_configs(results[k],v) if isinstance(v,dict) else v #Iterable不行  str也是Iterable
        else:
            results[k] = v # 原来没有 直接加
    return results

class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''
    def __init__(self, names=(), values=(), **kw):#可以传入names=('id','name') values=(123,'Tom')
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):# zip 打包成一对对的tuple组成的list [('id',123),('name','Tom')]
            self[k] = v
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)
    def __setattr__(self, key, value):
        self[key] = value

def toDict(d):
    results = Dict()
    for k,v in d.items():
        results[k] = toDict(v) if isinstance(v,dict) else v
    return results
    
try:
    import configs_override
    configs = merge_configs(configs,configs_override.configs)
except BaseException as e:
    pass

configs = toDict(configs)