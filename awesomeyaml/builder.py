# Copyright 2022 Samsung Electronics Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pathlib
import contextlib
import collections.abc as cabc

from .nodes.node import ConfigNode
from . import errors


class Builder():
    ''' A builder class responsible for merging multiple yaml configs into a single
        node.

        When populating a builder object, it will maintain a list of 'stages' with each
        stage being a single yaml document. :py:meth:`add_source` and :py:meth:`add_multiple_sources` can be
        used to add new stages - the first function should be given a source of yaml documents
        (e.g. a file) and will greedily read its content appending new documents to the list
        of stages (in order of reading). For more information about what can be a source
        for yaml documents, see :py:meth:`add_source`. :py:meth:`add_multiple_sources` simply proides a convenient
        way of adding multiple sources without calling :py:meth:`add_source` multiple times - its delegates
        all actual work to :py:meth:`add_source`.
        
        After all relevant stages have been added, they can be later merged into a single
        node by calling :py:meth:`build`.
    '''

    _default_safe_flag = True

    def __init__(self):
        ''' Creates an empty builder. Yaml documents can then be added with calls to :py:meth:`add_source`
            and :py:meth:`add_multiple_sources`.
        '''
        self.stages = []
        self._current_file = None
        self._current_stage = None

    @contextlib.contextmanager
    def current_stage(self, i):
        ''' A context manager used to mark a specific stage as 'currently being preprocessed'.

            The marking doesn't have any specific meaning imposed by this function, its responsibility
            of its user to interpret it.
            The function is intended to be used internally but is exposed here in case someone would
            like to derive from this class to customize preprocessing/merging of yaml documents.

            At the moment of writing this, the marking of the active stage is only used when recursively
            constructing subbuilders - which is used when recursively preprocessing include nodes (when a subbuilder
            is created, it reads the current stage id and saves it in order to be able to reconstruct
            a chain of includes, e.g. to report errors).

            Arguments:
                i (int, None) : index of the stage to be marked as active (can be ``None`` to indicate that no stage
                    is currently being preprocessed).

            Returns:
                A context manager which sets the current stage to ``i`` when entered and restored the previous
                values on exit.
        '''
        old = self._current_stage
        self._current_stage = i
        yield
        self._current_stage = old

    def get_next_stage_idx(self):
        ''' Returns index of an 'about-to-be-added' stage. This is basically always equal to the current length of the list of stages.
            The function is provided to enable easy change of this logic in case it's needed in the future.
        '''
        return len(self.stages)

    def get_current_stage_idx(self):
        ''' Return index of the stage 'currently being preprocessed', or ``None`` if no stage is being preprocessed.
            See :py:meth:`current_stage` and :py:meth:`preprocess` for more information about what 'being preprocessed' means.
        '''
        return self._current_stage

    def get_current_file(self):
        ''' Get name of the file currently being read - used by the yaml parser to include informations
            about origins of each node (especially important for include nodes).
            This can be ``None`` if the yaml content currently being parsed does not originate from a file.
        '''
        return self._current_file

    @errors.api_entry
    def add_multiple_sources(self, *sources, raw_yaml=None, filename=None, safe=None):
        ''' Adds multiple sources using :py:meth:`add_source` function. ``raw_yaml``, ``filename`` and ``safe`` have the same meaning
            as in :py:meth:`add_source` and can be either a single scalar, in which case its value is broadcasted
            and applied to all elements in ``*sources``, or they can be sequences of equal length if different
            values should be applied to different elements in ``*sources``. It's perfectly fine for one of them
            to be a scalar value and the second one to be a sequence.

            Returns:
                ``None``
        '''
        def sanitize(arg, arg_name):
            if not isinstance(arg, cabc.Sequence) or isinstance(arg, str) or isinstance(arg, bytes):
                arg = [arg] * len(sources)
            else:
                #if isinstance(arg, str) or isinstance(arg, bytes):
                #    raise ValueError(f"{arg_name!r}: Expected sequence but not str or bytes")
                if len(arg) != len(sources):
                    raise ValueError(f"Length of 'sources' and {arg_name!r} must match")

            return arg

        raw_yaml = sanitize(raw_yaml, 'raw_yaml')
        filename = sanitize(filename, 'filename')
        safe = sanitize(safe, 'safe')
        for source, raw, fname, sflag in zip(sources, raw_yaml, filename, safe):
            self.add_source(source, raw_yaml=raw, filename=fname, safe=sflag)

    @errors.api_entry
    def add_source(self, source, raw_yaml=None, filename=None, safe=None):
        ''' Parse a stream of yaml documents specified by ``source`` and add them to the list of stages.
            The documents stream can be provided either directly or read from a file - the behaviour is determined
            by ``source`` and ``raw_yaml`` arguments.

            Args:
                source : either a string or a file object. If it's a file object, it will be passed directly to the :py:func:`awesomeyaml.yaml.parse`,
                           otherwise it will be treated either as a filename or yaml to be parsed, according to ``raw_yaml``.
                raw_yaml : controls how ``source`` is interpreted if it is passed as string, possible cases are:

                            - if ``raw_yaml`` is set to ``None`` specifically (default), the function will try guessing whether ``source`` is a
                              name of a file or a yaml string to be parsed directly. In order to do that, it will behave as if ``raw_yaml`` was set to ``False``
                              and in case ``FileNotFoundError`` is raised it will fallback to the case when ``raw_yaml`` is set to ``True``.
                            - if ``bool(raw_yaml)`` evaluates to ``False`` and is not ``None``, the function will attempt to open and read content of a file named ``source``,
                              raising an error if such a file does not exist
                            - if ``bool(raw_yaml)`` evaluates to ``True``, ``source`` is treated as a yaml string and passed directly to the :py:func:`awesomeyaml.yaml.parse`

                filename : can be used to provide a custom filename that should be associated with the parsed ``source``, useful if ``source`` does not name a file
                            by itself, if not passed (``None``) and ``source`` names a file, the associated filename will be the one passed by ``source```, if ``source``
                            does not name a file and ``filename`` is not specified, parsed content will not have information about the source filename

                safe : specifies whether the parsed content should be considered safe for evaluation, some nodes parsed as unsafe will fail to evaluate for security
                        reasons (e.g., eval nodes); marking something as unsafe is contentious, while code marked as safe can still declare parts of itself as unsafe
                        from within the yaml (by using !unsafe or equivalent metadata); the exact rules for deducing safety of a node are summarized below::

                            - if a node is explicitly marked as !unsafe within yaml, it is unsafe
                            - otherwise, if it's a child of an unsafe node, it is unsafe
                            - otherwise, if it's included by a part of the code considered unsafe, it is unsafe
                            - for some node types, if a node is merged with an unsafe node, it might become unsafe itself
                            - otherwise, if a node comes from a source added with ``safe`` parameter set to ``False``, it is unsafe
                            - otherwise, if a node was parsed while the default safe flag (``Builder.set_default_safe_flag``) was set to ``False``, it is unsafe
                            - otherwise, it is safe

            Returns:
                ``None``
        '''
        if raw_yaml and not isinstance(source, str):
            raise ValueError('source is expected to be string and contain yaml to be parsed when raw_yaml is set to True')

        if isinstance(source, pathlib.Path):
            source = str(source)

        if isinstance(source, str) and not raw_yaml:
            try:
                with open(os.path.expanduser(source), 'r') as f:
                    self._current_file = source
                    source = f.read()
            except (FileNotFoundError, OSError) as e:
                #OSError(22) is "Invalid argument"
                #OSError(36) is "File name too long"
                if type(e) is OSError and e.errno not in [22, 36]:
                    raise
                if raw_yaml is not None:
                    raise

        try:
            if filename is not None:
                self._current_file = filename

            if safe is None:
                safe = self._default_safe_flag

            with ConfigNode.default_safe_flag(safe and self._default_safe_flag):
                with ConfigNode.default_filename(self._current_file):
                    from . import yaml
                    for node in yaml.parse(source, self):
                        if node is not None:
                            self.stages.append(node)
        finally:
            self._current_file = None

    @errors.api_entry
    def build(self):
        ''' Preprocesses all stages and merges them to construct a single config node.
            This node is suitable to be passed to :py:class:`awesomeyaml.eval_context.EvalContext`
            in order to be evaluated.

            Returns:
                A py:class:`awesomeyaml.nodes.ConfigDict` node representing merged config.
        '''
        if not self.stages:
            return None

        self.preprocess()
        self.flatten()
        return self.stages[0]

    @errors.api_entry
    def preprocess(self):
        ''' Preprocesses all stages.

            'Preprocessing' is a building step when each stage has an opportunity to modify itself
            without involving other stages. This is done mostly to handle things (nodes) which might
            require some knowledge about other fields in the stage and therefore must be run
            after parsing is done, but should also be run before merging as they might change the merging
            outcome.

            Internally, this is achieved by triggering ``on_preprocess`` on all nodes within the stage.
            The bahaviour of ``on_preprocess`` will obviously vary from node to node, but as a representative
            example :py:class:`awesomeyaml.nodes.include.IncludeNode` can be used. An include node is used to trigger
            inclusion of another yaml file into the stage (which might also have include nodes, in which
            case they will be preprocessed recursively). Whereas they don't necessarily require other
            nodes to be preprocessed, there are a couple of reasons they are not resolved within the yaml
            parser:

                - first of all for debugability - having an explicit intermediate step when include nodes are
                  present but not yet preprocessed enables the user to see if the config building processes
                  goes as desired,
                - second of all, which is a little bit related to the first one, we don't want to make
                  yaml parser fail in case a user made an error and the included file cannot be found - that
                  is because parsing might be triggered before include nodes should be preprocessed (e.g. parsed
                  config can be send over to a different machine, when it's put together and includes are resolved).
                  Although currently no use-case requires this separation, it makes the overall design more flexible
                  and helps define clear boundaries between different parts of the package.

            Obviously, include nodes have to be preprocessed before merging happens as the result will be subject
            to merging, which makes them a nice candidate to be handled in during the preprocessing stage.
        '''
        i = 0
        while i < len(self.stages):
            _i = i
            with self.current_stage(i):
                stage = self.stages[i]
                new_stage = stage.ayns.preprocess(self)

                if new_stage is not stage:
                    try:
                        self.stages[i:i+1] = new_stage.stages
                        i += len(new_stage.stages)
                    except AttributeError:
                        self.stages[i] = new_stage
                        i += 1
                else:
                    i += 1

            assert _i != i, 'infinite loop?'

    @errors.api_entry
    def flatten(self):
        ''' Flattens the list of stages be iteratively merging all stages into a single one.
            Merging happens in the same order in which stages are stored, i.e.::

                stages[0].merge(stages[1]).merge(stages[2])...

        '''
        for stage in self.stages:
            if not isinstance(stage, dict):
                raise ValueError('Not all stages are dictionaries')

        new_stage = self.stages[0].ayns.premerge(None)
        if new_stage is not self.stages[0]:
            try:
                self.stages[0:1] = new_stage.stages
            except AttributeError:
                self.stages[0] = new_stage

        with errors.rethrow(errors.MergeError, self.stages[0], None, None):
            self.stages[0].ayns._require_all_new([], 'the node comes from the first config tree in a merging sequence and the current config is empty')
        if len(self.stages) < 2:
            return

        root = self.stages[0]
        for i in range(1, len(self.stages)):
            root = root.ayns.merge(self.stages[i])

        self.stages = [root]

    def get_lookup_dirs(self, ref_point):
        ''' Yields of list of directories where files should be searched for.
            Used by include nodes.

            Arguments:
                ref_point : an optional reference file w.r.t. which the searching happens,
                    if provided, it's directory is always the first one to be returned by
                    the generator

            Yields:
                A list of lookup directories.
        '''
        if ref_point is not None:
            yield os.path.dirname(ref_point)
        yield os.getcwd()

    def get_subbuilder(self, requester):
        ''' Returns a subbuilder which can be used to recursively build substreams of yaml documents.

            A subbuilder is created to recursively trigger :py:meth:`preprocess`, for example when processing
            an include node.

            Arguments:
                requester : a path of the node which requests the subbuilder (mostly used for debugging)

            Returns:
                A :py:class:`awesomeyaml.builder.SubBuilder` object who parent is this builder.
        '''
        if self._current_stage is None:
            raise RuntimeError('SubBuilder requested when not processing any stage!')

        return SubBuilder(requester, self)


class SubBuilder(Builder):
    ''' A subbuilder which might be created to enable recursive building.
        It should be created with a call to :py:meth:`Builder.get_subbuilder`.

        A subbuilder managers its own list of stages which can be preprocessed independently
        from the stages of its parent (i.e. as a part of the preprocessing step of one of the
        parent's stages).

        Calling :py:meth:`build` on a subbuilder will trigger preprocessing but not flattening as this
        should be handled later when the parent enter its flattening step. Instead, a single
        :py:class:`awesomeyaml.nodes.stream.StreamNode` is created representing a list of stages which
        should be flattened later. When flattening, the stream node will be replaced with the result
        of flattening its list of stages.
    '''
    def __init__(self, srcnode, parent):
        ''' Creates a new subbuilder.

            Arguments:
                srcnode : a path to the node requesting the subbuilder (the node exists in parent)
                parent : a parent Builder
        '''
        super().__init__()
        self.requester = srcnode
        self.parent = parent
        self.stage = parent.get_current_stage_idx()

    def build(self):
        ''' Triggers :py:meth:`preprocess` on the list of stages handled by this subbuilder.
            Intended for recursive preprocessing.

            Returns:
                A :py:class:`awesomeyaml.nodes.stream.StreamNode` holding a list of preprocessed stages.
                The stages attached to it will be flatten with the parent stage of the stream
                node.
        '''
        from .nodes.stream import StreamNode
        self.preprocess()
        return StreamNode(self)

    def get_lookup_dirs(self, ref_point):
        return self.parent.get_lookup_dirs(ref_point)
