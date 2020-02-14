from .node import ConfigNode


class DynamicNode(ConfigNode):
    def __init__(self, dependencies=None, users=None, **kwargs):
        super().__init__(**kwargs)

        self._dependencies = dependencies or []
        self._users = users or []

        assert isinstance(self._dependencies, list)
        assert isinstance(self._users, list)
        for d in self._dependencies:
            assert isinstance(d, str)
        for u in self._users:
            assert isinstance(u, str)

        self._deps_cross_set = not self._users and not self._dependencies

    def cross_set_deps(self, path, top):
        if self._deps_cross_set:
            return

        for user_name in self._users:
            user_name = user_name.format(**globals(), **locals())
            user, present = top._abs_find(user_name)
            if present and isinstance(user, Dynamic) and user is not self:
                if user.uses(path, user_name):
                    log.Log().log(f'!!! Warning: recursive usage between {path!r} and {user_name!r} -- the order of execution cannot be guaranteed, this may cause errors.')

                if not user.depends_on(path, user_name):
                    user._dependencies.append(path)

        for dep_name in self._dependencies:
            dep_name = dep_name.format(**globals(), **locals())
            dep, present = top._abs_find(dep_name)
            if present and isinstance(dep, Dynamic) and dep is not self:
                if dep.depends_on(path, dep_name):
                    log.Log().log(f'!!! Warning: recursive depedency between {path!r} and {dep_name!r} -- the order of execution cannot be guaranteed, this may cause errors.')
                
                if not dep.uses(path, dep_name):
                    dep._users.append(path)

        self._deps_cross_set = True

    def evaluate(self, path, top):
        if hasattr(self, '_guard'):
            raise RuntimeError('Recursive evaluation is prohibited')

        if not self._deps_cross_set:
            self.cross_set_deps(path, top)
            return self

        priority = self.calc_priority(path, top)
        assert priority is not None
        if priority > self._priority:
            return self.postpone(priority)

        setattr(self, '_guard', None)
        try:
            for dep_name in self._dependencies:
                dep_name = dep_name.format(**globals(), **locals())
                dep, present = top._abs_find(dep_name)
                if not present or isinstance(dep, InvalidNode):
                    raise RuntimeError(f'Dependency {dep_name!r} for node {path!r} is missing')

            ret = self.evaluate_impl(path, top)
        except:
            delattr(self, '_guard')
            raise
        
        delattr(self, '_guard')
        return ret

    def calc_priority(self, path, top):
        assert self._priority is not None
        priority = self._priority
        for dep_name in self._dependencies:
            dep_name = dep_name.format(**globals(), **locals())
            dep, present = top._abs_find(dep_name)
            if present and isinstance(dep, Dynamic) and dep is not self:
                if not dep.depends_on(path, dep_name) and dep._priority is not None:
                    if priority is None:
                        priority = dep._priority
                    else:
                        priority = max(priority, dep._priority+1)

        return priority

    def evaluate_impl(self, path, top):
        raise NotImplementedError()

    def get_priority(self):
        return self._priority

    def postpone(self, new_priority):
        #self.dependencies.clear()
        self._priority = new_priority
        return self

    def depends_on(self, name, path):
        name = name.format(**globals(), **locals())
        return name in self._dependencies

    def uses(self, name, path):
        name = name.format(**globals(), **locals())
        return name in self._users

    def _represent(self, dumper):
        raise NotImplementedError()

    def _get_base_mapping(self, dumper):
        ret = {}
        if self._priority != 0:
            ret['priority'] = self._priority
        if self._dependencies:
            ret['dependencies'] = self._dependencies
        if self._users:
            ret['users'] = self._users
        return ret