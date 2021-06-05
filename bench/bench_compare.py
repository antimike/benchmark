import time
from abc import ABC, abstractmethod
from functools import partial
import logging
from enum import Enum, auto
from typing import Optional, Union, Callable, TypeVar, Any, NamedTuple, TypedDict, Collection
from collections.abc import Sequence, Mapping
from inspect import signature

T = TypeVar('T')

class FUNCTION_LOG_EVENTS(Enum):
    BIND_FAILURE = 'bind_failure'
    ENTERED = 'entered'
    RETURNED = 'returned'
    EXITED = 'exited'
    EXCEPTION = 'exception'

class BENCHMARK_EVENTS(Enum):
    TIME = 'time'

LOG_LEVELS = Enum('LOG_LEVELS', logging._nameToLevel)

_FlogEvent = TypedDict('_FlogEvent', msg=str, level=LOG_LEVELS)
_FlogEventMap = TypedDict('_FlogEventMap', {e: _FlogEvent for e in FUNCTION_LOG_EVENTS})
class _BenchmarkEventMap(_FlogEventMap):
    BENCHMARK_EVENTS.TIME: _FlogEvent

_LoggerDefaults = {
    'indent': '\t'
}

class FunctionLogEventOptions(_FlogEventMap, Options):
    pass

class Options(TypedDict):

    @classmethod
    @abstractmethod
    def defaults(cls):
        return NotImplemented

    @classmethod
    def parse(cls, inputs):
        pass

def RecursiveMapping(KeyType: Type = str, ValueType: Type = str, BaseType: Mapping = dict):
    return BaseType[KeyType, Union[ValueType, jkkkj]]

class AddressDict(TypedDict):

    def __init__(self, schema: Mapping[Any, Union[AddressDict, TypedDict]], delimiter='_'):
        pass



_FlogEventDefaults: _FlogEventMap = {
    FUNCTION_LOG_EVENTS.BIND_FAILURE: _FlogEvent({
        'msg': "Failed to bind arguments %(args)s and keywords %(kwargs)s to function '%(__name__)s'",
        'level': LOG_LEVELS.ERROR
    }),
    FUNCTION_LOG_EVENTS.ENTERED: _FlogEvent({
        'msg': "Calling function '%(__name__)s' with parameters %(args)s and keywords %(kwargs)s:",
        'level': LOG_LEVELS.INFO
    }),
    FUNCTION_LOG_EVENTS.RETURNED: _FlogEvent({
        'msg': "%(indent)sReturned value %(return)s",
        'level': LOG_LEVELS.INFO
    }),
    FUNCTION_LOG_EVENTS.EXITED: _FlogEvent({
        'msg': "Exited function '%(__name__)s'",
        'level': LOG_LEVELS.INFO
    }),
    FUNCTION_LOG_EVENTS.EXCEPTION: _FlogEvent({
        'msg': "%(indent)sException of type '%(exception_type)s' raised",
        'level': LOG_LEVELS.ERROR
    })
}

_BenchmarkEventDefaults: _BenchmarkEventMap = _FlogEventDefaults | {
        BENCHMARK_EVENTS.TIME: _FlogEventMap({
            'msg': "%(indent)sExecution time: %(time)s",
            'level': LOG_LEVELS.INFO
        }),
        FUNCTION_LOG_EVENTS.ENTERED: _FlogEventMap({
            'msg': "Benchmarking '%(__name__)s' with parameters %(args)s and keywords %(kwargs)s:",
            'level': LOG_LEVELS.INFO
        })
    }

def _create_options_type(name: str, options_dict: Mapping[Any, Any]) -> NamedTuple[str]:
    return namedtuple(
        name,
        options_dict,
        defaults = options_dict.values()
    )

def _squash_dict(d):
    ret = {}
    for key, val in d.items():
        key = key.value if isinstance(key, Enum) else key
        try:
            ret.update(
                {key + '_' + subkey: subval for subkey, subval in val.items()}
            )
        except AttributeError:
            ret.update(key=val)
    return ret

def _unsquash_dict(d, subdict_type, enum):
    ret = {}
    subdict_keys = subdict_type.__annotations__.keys()
    for key, val in d.items():
        if any(map(lambda subkey: key.endswith('_' + subkey), subdict_keys)):
            newkey, subkey = key.split('_', maxsplit=2)
            ret.setdefault(newkey, {}).update(subkey, val)
        else:
            ret.setdefault(key, {}).update(key, val)
    return ret

FunctionLogOptions = _create_param_namedtuple(
    _squash_dict(_FlogEventDefaults | _LoggerDefaults)
)

BenchmarkOptions = _create_param_namedtuple(
    _squash_dict(_BenchmarkEventDefaults | _LoggerDefaults)
)

GenericLogger = Callable[[str, LOG_LEVELS], None]

class FunctionLogger(NamedTuple):
    def __init__(self, options: FunctionLogOptions, logger: GenericLogger) -> None:
        for name, template in [(opt, val) for opt, val in options.items() if opt.endswith('_msg')]:
            setattr(self, name.replace('_msg', ''), lambda selfobj: logger(template % selfobj.params, level))

class FunctionLogger:
    def __init__(self, logger: Optional[BenchtoolLogger] = None, log_level: LOG_LEVELS = None):
        logger = logger or print
        try:
            self._logger = partial(logger.log, log_level or LOG_LEVELS.INFO)
        except AttributeError:
            self._logger = logger

def bench_compare_multiple(logger, *param_groups, **fn_names):
    """
    Facility to benchmark several functions on multiple groups of inputs

    :param logger: Construct to use for logging and printing results
        Can either be an arbitrary callable (e.g., 'print') or a logging.Logger object
    :param param_groups: Iterable of parameter groups which will be input to the passed functions one by one
    :param fn_names: Dictionary of functions to benchmark
    """
    title_str, ans_str, time_str = "Testing {name}:","\t{name}({params}) = {ans}","\tTime = {time}"
    for name, fn in fn_names.items():
        str_params = {'name': name}
        print(title_str.format(**str_params))
        for pg in param_groups:
            str_params |= {'params': pg}
            try:
                start = time.time()
                result = fn(*pg)
                exec = time.time() - start
            except TypeError:
                start = time.time()
                result = fn(pg)
                exec = time.time() - start
            str_params |= {'time': exec, 'ans': result}
            print(ans_str.format(**str_params))
            print(time_str.format(**str_params))

BenchtoolLogger = Union[logging.Logger, Callable[[str, ...], None]]
Args = Sequence[Any]
Kwargs = Mapping[str, Any]

class Benchtool:
    def __init__(self, logger: Optional[BenchtoolLogger] = None, log_level: LOG_LEVELS = None):
        logger = logger or print
        try:
            self._logger = partial(logger.log, log_level or LOG_LEVELS.INFO)
        except AttributeError:
            self._logger = logger
    def benchmark(self, fn: Callable[..., Any], args: Sequence[Args], kwargs: Optional[Sequence[Kwargs]] = None, name: Optional(str) = None):
        name = name or fn.__name__


