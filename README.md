# AwesomeYaml

AwesomeYaml is a Python-based library which extends standard yaml with a set of custom tags and a processing pipeline designed to make the process of building and manipulating yaml-based config files easier.
We use a popular [pyyaml](https://pypi.org/project/PyYAML/) package as the core component to read and write yaml files.

> **Note:** AwesomeYaml is *NOT* designed to be safe! Be cautious when using it with externally provided content.

## Content
 - [Overview](#AwesomeYaml)
   - [Capabilities](#Capabilities)
   - [Installation](#Installation)
   - [Running Tests](#Running-tests)
   - [Generating documentaion](#Generating-documentation)
 - [Quick reference](#Quick-reference)
   - [Low-level API](#Low-level-API)
 - [Detailed description](#Detailed-description)
   - [Yaml](#Yaml-side)
     - [Merging](#Merging-yaml-files)
     - [Yaml streams](#Yaml-streams)
     - [Evaluation](#Evaluation-of-nodes)
     - [Metadata](#Adding-user-defined-metadata)
   - [Python](#Python-side)
     - [Basic usage](#Basic-usage)
     - [Command line](#Handling-command-line-arguments)
     - [Accessing data](#Accessing-evaluated-fields)
   - [Tags summary](#Summary-of-extended-tags)
 - [Contributing](#contributing)
 - [Reporting issues](#reporting-issues)
 - [License](#license)

## Capabilities

Briefly speaking, `awesomeyaml` is capable of:
 - merging multiple (partial) config files into a common config object, allowing for:
   - cross-referencing elements from different files and expressing dependencies
   - controlling the merging process by defining 3 priorities and allowing the user to set them arbitralily for any entity within the config tree
   - moving and deleting entire subtrees during the merging process for easier wrapping of components
   - including files, supporting nested and within-the-tree includes
 - dynamically evaluating content of the nodes in the config tree, supporting:
   - f-string-like mechanism to evaluate strings
   - importing and embedding python entities directly in the evaluated config tree
   - calling python entities with the provided arguments (or binding arguments to them)
   - evalauting arbitrary python code (**UNSAFE!**) 
 - attaching user-defined metadata to any node in the config tree via a generic yaml-compatible mechanism


## Installation

Awesomeyaml requires `pyyaml` and `Python>=3.6`.
You can install `awesomeyaml` from PyPI by simply issuing:
```bash
python -m pip install awesomeyaml
```

Alternatively, you can also perform installation by cloning this repo and installing directly from it with pip:
```bash
git clone https://github.com/SamsungLabs/awesomeyaml.git
python -m pip install ./awesomeyaml
```

Optionally, you can add `-e` option to allow for in-place (also called editable or developer) installation:

```bash
python -m pip install -e ./awesomeyaml
```

or, if you don't need the repo to be laying around simply install directly from github:

```bash
python -m pip install https://github.com/SamsungLabs/awesomeyaml/tarball/master#egg=awesomeyaml
```

## Running tests

We use a standard `unittest` python package for writing tests.

Since `awesomeyaml` is a pure python library with minimal dependencies and does not directly depend on any OS or HW specific components, it is rather unlikely that a version tested on one machine would break on another.
However, if you want to be extra safe, you can run tests provided with the repo by using the following command (run from the cloned directory):

```
python -m unittest discover -v -s . -p '*_test.py'
```

You should see output ending with something similar to:

```
----------------------------------------------------------------------
Ran 118 tests in 0.131s

OK
```

If any errors have occurred, they should be mentioned at the end instead of `OK`.
Please [raise an issue]() if you encounter any.

> **Note:** the tests are only shipped with the repo, so you need to clone it in order to run them. Installing the cloned code is not required as the testing code always uses the code provided in the repo (by altering `sys.path`).

## Generating documentation
To automatically generate API documentation for the library, make sure `sphinx` and `sphinx_rtd_theme` are installed first.
You can easily install them with `pip`:
```bash
pip install sphinx sphinx_rtd_theme
```

> **Note:** `sphinx_rtd_theme` is only required if you want to use the readthedocs theme (the default one for this project).
> You can change the theme used by modifying your `docs/source/conf.py` file.

After installing `sphinx`, go to `docs/` and execute `make html`.
Your newly generated documentation should be available at `docs/build/index.html`.

# Quick reference

Use `awesomeyaml.Config` for default, out-of-the-box behaviour.
Specifically, to build a config from a sequence of yaml sources, use:
```python
import awesomeyaml as ay
with open('file2.yaml', 'r') as f:
    # read yaml from: filename, file object and inline yaml
    cfg = ay.Config.build('file1.yaml', f, 'field: !!null')
```

alternatively, you can let awesomeyaml parse part of your command line arguments and handle filenames and inline overwrites:

```python
import argparse
import pathlib

import awesomeyaml as ay

parser = argparse.ArgumentParser()
# add some custom arguments
parser.add_argument('--debug', action='store_true')
# identify arguments which should be used to build config
parser.add_argument('yamls', action='append')
args = parser.parse_arguments()

# optional function to lookup yaml files in a non-standard way
_lookup_dirs = ['.', '~/.project']
def lookup(filename):
    for d in _lookup_dirs:
        candidate = pathlib.Path(d).joinpath(filename).expanduser()
        if candidate.exists():
            return str(candidate)

    return filename

cfg = ay.Config.build_from_cmdline(*args.yamls, filename_lookup_fn=lookup)
```

Access fields in a dict by either standard indexing operator or by attribute names: `cfg['field']` is the same as `cfg.field`; consequently, access awesomeyaml API via a proxy object (namespace), e.g.: `cfg.ayns.children()`

## Low-level API
Use `awesomeyaml.Builder` to merge multiple yaml sources without evaluating dynamic nodes.
Use `awesomeyaml.EvalContext` to evaluate merged config:

```python
import awesomeyaml as ay

# merge multiple files
builder = ay.Builder()
builder.add_source('file1.yaml')
builder.add_multiple_sources('file2.yaml', 'field: !!null')
cfg = builder.build()

# evaluate dynamic nodes in cfg
eval_ctx = ay.EvalContext(cfg)
cfg = eval_ctx.evaluate()
# at this point cfg should be roughly the same as cfg from the first example
```

Use `awesomeyaml.yaml` for core functionality of reading and writing yaml files and to add support for custom tags.

```python
import awesomeyaml as ay
import awesomeyaml.yaml as ayyaml

#
# Read and write files with support for awesomeyaml tags
#

with open('file1.yaml', 'r') as f:
    # optionally pass filename as well to make
    # e.g. include nodes know were they come from,
    # otherwise everything is done w.r.t to the
    # current working directory
    # you can also pass awesomeyaml.Builder instance
    # for more complete functionality,
    # this is what happens normally when using
    # higher-level functions
    obj = ayyaml.parse(f.read())

ayyaml.dump(obj, 'file1_copy.yaml')


#
# define custom yaml constructor
#

# returned value should be derived from `awesomeyaml.nodes.ConfigNode
class MyNodeType(ay.nodes.ConfigNode):
    pass

def my_node_constructor(loader, node):
    # expects scalar value
    return MyNodeType(loader.construct_scalar(node))

# ayyaml.yaml is the standard yaml package used by awesomeyaml
ayyaml.yaml.add_constructor('!mynode', my_node_constructor)
```

See the [summary of the extended tags](#Summary-of-extended-tags) for an overview of extra tags implemented by awesomeyaml.

# Detailed description

## Introduction

Awesomeyaml was originally developed to make it easier to work with multiple configuration files, therefore it shines especially when configuration has a modular nature -- i.e., different parts of the system can be configured independently from each other, but at the same time might introduce requirements for each other, etc.
A prominent example of such a system could be a machine learning project which supports multiple models, datasets and optimization techniques.
Usually, each of these elements can be configured independently from the rest, e.g., the dataset configuration can include parameters for a common preprocessing done for this dataset regardless of what model is used.
Analogically, the model configuration can also be done mostly independently from the dataset in use, however, it does contain some parameters which are strictly determined by the dataset - e.g., for an image classification network that would be a number of classes for the last layer.

As mentioned before, to help dealing with situations like that, awesomeyaml is designed to work with configurations which are split into multiple files.
For example, following the machine learning analogy, the configuration could be split in the following way:

```
+ configs
|   + datasets
|   |    dataset1.yaml
|   |    dataset2.yaml
|   |
|   + models
|   |    model1.yaml
|   |    model2.yaml
|   |
|   + optimizers
|        optim1.yaml
|        optim2.yaml
|
+ train.py
```

we would like to be able to call `train.py` with a set of 3 config files by selecting any one of datasets, models and optimizers, e.g., let us train model1 with dataset2 and optimizer2:

```
python train.py configs/models/model1.yaml configs/datasets/dataset2.yaml configs/optimizers/optim2.yaml
```

or use the same setting but try a different optimizer:

```
python train.py configs/models/model1.yaml configs/datasets/dataset2.yaml configs/optimizers/optim1.yaml
```

In both cases, the command line arguments define a sequence of config files which need to be processed to construct the final form of the config - we call this process **building** and split it into two parts: *1)* **merging** of the provided config files, and *2)* **evaluating** dynamic elements.
The following code snippet presents the basic idea behind building a config object:

```python
def build_config(*yaml_sources):
    merged_cfg = merge(yaml_sources)
    evaluated_cfg = evaluate(merged_cfg)
    return evaluated_cfg
```

Merging of the yaml files is handed by `awesomeyaml.Builder` and evaluation is done by `awesomeyaml.EvalContext`, with `awesomeyaml.Config` being the top-level class encapsulating both steps in a standard way presented in the code snippet above.

The following documentation is split into two parts.
The first talks about working with yaml files and how awesomeyaml functionality helps with that.
The second concerns awesomeyaml Python's API and how to achieve the behaviour explained in the first part.

## Yaml side
### Merging yaml files

Let us begin by providing some examples of how the config files could look like/ For example, consider the content of the `model1.yaml` file like the following:

```yaml
---
model:
    name: MyAwesomeCNN
    channels: 64
    stacks: 3
    classes: !required
```

The file is a pretty straightforward yaml file which defines a set of parameters grouped under a common `"model"` key.
The only unusual thing is the non-standard `!required` tag - this tag is provided by awesomeyaml and can be used to identify parameters which are introduced (and required) by a specific part of the system but should be defined by other parts of the system.
In our case specifically, we want to say that our model needs to know how many classes are to be used but this value should be defined somewhere else (as mentioned earlier, this is defined by the choice of a dataset).
Following this, we could further define the `dataset1.yaml` file as:
```yaml
---
dataset:
    name: cifar100
    folder: ~/data/cifar100
    process:
        random_vflip: 0.5
        cutout: 3
        normalize: [[0.4914, 0.4822, 0.4465], [0.2023, 0.1994, 0.2010]]

model:
    classes: 100
``` 

In both cases the final config, which will be used by the training script, will be *build* by reading and *merging* the content of the consecutive config files in the provided sequence.

Merging is performed by reading and combing files sequentially, strictly in a user-defined order (more about it can be found in the Python part).
We carefully define the rules of combing elements and provide ways of manipulating them which are explained in details later.
However, the most typical (and intuitive) example would be merging of two dictionaries where elements with common keys are overwritten with their value from the newer dict and all the others are taken from either of the dicts (no elements are removed).
This is what would happen most of the time when merging content `model1.yaml` with `dataset1.yaml`, since both files contain mostly simple dictionaries.
Specifically, if the merging order is defined as:  
`model1.yaml <- dataset1.yaml`  
then the content of `dataset1.yaml` will be used to update content of `model1.yaml` and the expected result would be:

```yaml
---
dataset:
    name: cifar100
    folder: ~/data/cifar100
    process:
        random_vflip: 0.5
        cutout: 3
        normalize: [[0.4914, 0.4822, 0.4465], [0.2023, 0.1994, 0.2010]]

model:
    name: MyAwesomeCNN
    channels: 64
    stacks: 3
    classes: 100
```

Please note that the value of `model.classes` was overwritten with from the original `!required` to `100`.
ALso, please note that in general merging operation is non-commutativie, meaning that merging `A <- B` and `B <- A` can result in different outcomes.
For example, in our example above, if the merging order was swappedt he value `100` would be overwritten with `!required`.

### Yaml streams
Yaml includes a built-in mechanism for including multiple "files" inside a single physical file.
This is achieved by separating contents with a line containing `---`.
Awesomeyaml supports reading yaml sources with more than one "file" inside them - we call such entities yaml streams (the term also covers multiple yaml sources defined outside of yaml).

Yaml streams can be nested.
For example, consider a user-defined list of files: `['file1.yaml', 'file2.yaml']`.
This list is a yaml stream with two sources.
Now, suppose `file1.yaml` has the following structure:

```yaml
---
!include file3.yaml
---
foo: !include [file4.yaml, file5.yaml]
```

Here, `!include` is one of the extended tags introduced by awesomeyaml.
The tag read content of a file and embeds it in the parent file - either as a top-level entitiy (`file3.yaml`) or as a subelement of a node (`file4.yaml` and `file5.yaml`).
If more than one file is provided to `!include`, the files are merged recursively before being embedded.
Putting it all together, after considering nested stream, our example expands from a single stream of two files to nested streams which need to be merged in a correct order to eventually form a single, final config.
The snippet below roughly illustrates how this process progresses:

```
1. file1.yaml <- file2.yaml
2. [file3.yaml <- { foo: [file4.yaml <- file5.yaml] }] <- file2.yaml
3. file3.yaml <- { foo: content } <- file2.yaml
4. final_config
```

### Evaluation of nodes

Apart from merging, another important aspect of awesomeyaml is support for lazily-evaluated nodes.
The requirement behind laziness comes from the fact that when a single yaml file is parsed - that is, before merging - the final content of the config object is not yet defined, so any node who content depends on another node's value could evaluate to an undesired value.
This is also one of the reasons why evaluation happens after merging is performed.

Consider the following example, where we add a short section to the config file defining the experiment directory:

```yaml
---
fs:
    root: ~/.project
    exp_folder: !path [!xref fs.root, !xref model.name]
```

We define the experiment folder (`fs.exp_folder`) with respect to the root folder (`fs.root`) by appending the selected model's name.
By doing so, each model will have it's own experiment directory.
Obviously, we could create a deeper structure by considering other elements, like dataset, but for the purpose of this example one extra level is enough.

The `!path` node in this example is used to define and manipulate paths - in this specific case, during evaluation phase, it will try joining the two elements in its list to form the final path.
The `!xref` argument, on the other hand, is used to cross-reference another node in the config - that is, use its value in another place.
Both of these nodes are examples of nodes which are evaluated lazily.
You can see the reason why in the example itself - even though the first parameter in `fs.exp_folder` could be evaluated eagerly, the second one references a node which does not exist in this file - the expectation is that it will be defined later.

> **Note:** For more user-friendly behaviour, the example could also set `model.name` to `!required` to make sure that the error messages are more meaningful.

Therefore, eager execution would always result in an error.
What is more, even if the missing value was defined, we still would like to allow the user to overwrite some of the values later.
All this makes the value of the entire `fs.exp_folder` undefined at the moment of parsing of the yaml file.

For more information about what nodes are executed lazily and what they do, please see the [summary of tags](#Summary-of-extended-tags).

### Adding user-defined metadata

Awesomeyaml allows its users to assign arbitrary metadata to any of the nodes in the config - this is done by (ab)using yaml tag mechanism.
At the core level, metadata are stored as a postfix to any tag which contains hex-encoded result of pickling python literals - this tag suffix can potentially be added to any other tag.

> **Note:** although not directly enforced, official support for metadata is only limited to the cases where the top level element is a `dict`. You can try encoding other literals and there's a chance that everything will be fine (since internally metadata are unused), but we do not guarantee anything. Also, as explained later, our syntax extension only supports `dict` types.

To further explain the process of encoding metadata, consider the following yaml file which extend the previous example with some caching parameters:
```yaml
---
fs:
    root: ~/.project
    exp_folder: !path [!xref fs.root, !xref model.name]
    cache: !path [ !xref fs.root, cache ]
    cache_size: 16GB
    caching_policy: lru
```

Let's say, that the `fs.caching_policy` is an argument expecting one of the following values: `['lru', 'fifo', 'filo']` and the user would like to embed this information (to later handle validation of the passed value) in a form of the following metadata dict:
```python
{ 'available_options': ['lru', 'fifo', 'filo'] }
```

In order to form a valid yaml document, the python code defining the metadata needs to be encoded by pickling the desired value and encoding the resulting stream of bytes using hexadecimal literals.
For the example above, this goes roughly like:
```python
import pickle
metadata = { 'available_options': ['lru', 'fifo', 'filo'] }
encoded = pickle.dumps(metadata).hex()
print(encoded)
# prints '80037d71005811000000617661696c61626c655f6f7074696f6e7371015d71022858030000006c7275710358040000006669666f7104580400000066696c6f710565732e'
```

After the encoded metadata are obtained, they can be added to any tag as a suffix, separated by `:` from the main tag.
Since in the example above the target node does not have any tag, we can add a simple `!metadata` tag which does nothing except serving as a way to add metadata
to an otherwise standard node.
The final form would then look like:
```yaml
fs:
    root: ~/.project
    cache: !path [ !xref fs.root, cache ]
    cache_size: 16GB
    caching_policy: !metadata:80037d71005811000000617661696c61626c655f6f7074696f6e7371015d71022858030000006c7275710358040000006669666f7104580400000066696c6f710565732e lru
```

Although, encoding metadata in this form has the benefit of being compatible with standard yaml, it is obvious that this form is neither easy to write nor read by humans.
Therefore, even though at its core awesomeyaml will use the aforementioned mechanism to store and read metadata, it also provides a human-friendly way of defining metadata by extending yaml syntax a little bit.
Specifically, instead of using `!tag:encoded_metadata` syntax, the user can: `!tag{{ metadata }}` non-standard syntax, where `metadata` is content of the metadata dict in plain python.

Using the extended metadata syntax, the example above becomes:
```yaml
fs:
    root: ~/.project
    cache: !path [ !xref fs.root, cache ]
    cache_size: 16GB
    caching_policy: !metadata{{ 'available_options': ['lru', 'fifo', 'filo'] }} lru
```

## Python side
### Basic usage

Following the example command lines above, the desired behaviour could be achieved by using `awesomeyaml.Config.build` static method, for example:


```python
# train.py
import awesomeyaml as ay

cfg = ay.Config.build('configs/models/model1.yaml',
    'configs/datasets/dataset2.yaml',
    'configs/optimizers/optim2.yaml')
```

or, in a more generic way:

```python
# train.py
import sys
import awesomeyaml as ay

cfg = ay.Config.build(*sys.argv[1:])
```

### Handling command-line arguments

Please note that awesomeyaml does not perform any sophisticated command line parsing, so the example above with `sys.argv` can easily break it.
Specifically, the `awesomeyaml.Config.build` method expects all its arguments to be either of:
 - a filename
 - a file object
 - yaml string

Because of that, it's advised to use `argparse` to extract arguments which are meaningful for awesomeyaml and preprocess the rest independently.

However, there is one extra thing awesomeyaml is capable of with regard to command line processing - it can construct valid yaml from one-liners which can be used to overwrite a specific value. Consider the following example: we'd like to train `model1` with `dataset2` and `optim2` (as in the examples before) but we want to experiment with different number of channels. It is impractical to create a new config file each time we want to change just a single value, so we try to overwrite the default values by appending some yaml to the command line:

```bash
# try the model with 16 channels, instead of 64
python train.py configs/models/model1.yaml configs/datasets/dataset2.yaml configs/optimizers/optim2.yaml "model: { channels: 16 }"
```

The example above works by first merging content defined in the files and then with the content defined with inlined yaml.
However, specifying a full yaml structure to simply overwrite a single value introduce unnecessary burden and makes it hard to quickly change some values from the command line.
Therefore, the user is free to use a shorted form where the target node is specified with syntax similar to accessing attributes of the evaluated config (see [below](#Accessing-evaluated-fields)) and its new value is given after `=`.
For example, the number of channels in our previous example could be overwriten with:
```bash
model.channels=16
```

> **Note:** It is important to make sure that the entire expression is passed as a single argument. This can be achieved by either not putting spaces around `=` or using quotes.

However, expressions like the one above are not valid yaml and hence cannot be used directly with `awesomeyaml.Config.build`.
Instead, awesomeyaml provides another function `awesomeyaml.Config.build_from_cmdline` which is capable of identifying and transforming those expressions into their full-yaml form (like the one in the first example) suitable to be given to the standard `build` function.

See [quick reference](#Quick-reference) for a short example of how handling of the command line arguments could be done.

### Accessing evaluated fields

Awesomeyaml implements the [bunch](https://pypi.org/project/bunch/) pattern for all its `dict`-like objects, including the main config object.
Therefore, after the config object is built, its content can be accessed either by using standard indexing operator (like normal `dict`) or through attribute names.
Following our example from above, the following lines are analogical:
```python
obj1 = cfg['a']
obj2 = cfg.a
assert obj1 is obj2
```
The bunch pattern is applied recursively to all dictionaries so it's possible to chain attributes.

However, using the bunch pattern introduces certain problems.
Specifically, because it is possible in Python to shadow methods and other class-level attributes with instance-level attributes, it is fairly easy to introduce undesired conficts between attributes introduced by reading the user's config file and either internal or external API of awesomeyaml's entities.

For example, [ComposedNode](awesomeyaml/nodes/composed.py) class, which is the base class for both lists and dicts within awesomeyaml, provides a common interface for iterating and manipulating sub-nodes of a node. One of the methods introduced by this class is called `children` and can be used to simply iterate over sub-nodes.
However, it is quite likely that a key `"children"` would appear inside the user's config file,
e.g., if the config file describes some tree-like structure.
In that case, any code which would access `obj.children` with the intention of calling the awesomeyaml function would instead access the value read from the config file, most likely resulting in an error.

To avoid name conflicts and still be able to use the bunch pattern, we decided to introduce two rules:
 - the bunch pattern does not pick up names starting with `_`, that means that any internal method, attribute etc. can be safely accessed by its names; from the end-user's perspective, that also means that if a name starting with an `_` appears in the `.yaml` file, it can only be accessed by the standard indexing operator, e.g.: `cfg['_some_field']`
 - all other methods and attributes which are part of the awesomeyaml API are put under `ayns` namespace - in order to access them, one needs to go through the proxy called `ayns`, e.g. to access the previously mentioned `children` method, the relevant call would look like: `cfg.ayns.children()`
 > **Note:** it is still possible to shadow `ayns` name with a value from a config file as there are no checks to prevent this, therefore the user should be careful about (not) using this name - including it in a config file would result in undefined behaviour.


## Summary of extended tags
This section includes a brief summary of the new tags introduced by awesomeyaml, each with a short description and a link to more information.
Please note that many tags supports more than one syntax and the behaviour of some can be achieved in different way than using the tag.
In either case, more information can always be found in the provided link to documentation.

> **Note:** For the links to work, please [generate html documentation](#generating-documentation)

| Tag | Description | Doc |
|-|-|-|
| `!append [list]` | Appends to an existing list on merge | [AppendNode](docs/build/html/awesomeyaml.nodes.append.html) |
| `!bind:name { args }` | Binds arguments `args` to a python entity called `name` | [BindNode](docs/build/html/awesomeyaml.nodes.bind.html) |
| `!call:name { args }` | Calls a python entity called `name` with arguments `args` | [CallNode](docs/build/html/awesomeyaml.nodes.call.html) |
| `!eval code` | Evaluates arbitrary python `code` | [EvalNode](docs/build/html/awesomeyaml.nodes.eval.html) |
| `!fstr str` | Evaluates an f-string expression `str` | [FStrNode](docs/build/html/awesomeyaml.nodes.fstr.html) |
| `!import name` | Embeds a python entity called `name` | [ImportNode](docs/build/html/awesomeyaml.nodes.import.html) |
| `!include file` | Includes another config `file` recursively | [IncludeNode](docs/build/html/awesomeyaml.nodes.include.html) |
| `!path:ref [joins]` | Computes a path, starting with a reference point `ref` and then following a list of folders in `joins` | [PathNode](docs/build/html/awesomeyaml.nodes.path.html) |
| `!prev node` | Moves the content of `node` to a new place on merge | [PrevNode](docs/build/html/awesomeyaml.nodes.prev.html) |
| `!required` | Specifies that a value should be provided later | [RequiredNode](docs/build/html/awesomeyaml.nodes.required.html) |
| `!xref node` | Cross-references another node | [XRefNode](docs/build/html/awesomeyaml.nodes.xref.html) |
| `!null` | Evaluates to `None` | N/A |
| `!metadata:str` | Embeds metadata encoded in `str` to a node | [Metadata]() |
| `!weak` | Changes a node's priority to low | [Merging]() |
| `!force` | Changes a node's priority to high | [Merging]() |
| `!del` | Replaces the content of a matching node on merge | [Merging]() |
| `!merge` | Merges the content of a matching node on merge | [Merging]() |


## Contributing

All contributions are welcome, please open a pull request with your changes!

If a substantial change is accepted and merged into the codebase the author might be asked to own contributed pieces of code and become responsible for reviewing/maintaining those parts.
Lack of commitment to fulfil this obligation might result in reverting any changes, arbitrary changes of ownership, or any other actions deemed necessary to allow for healthy development of the package.

When making your changes, please follow the coding style used throughout the project (PEP-8).


## Reporting issues

Please open an issue on GitHub and provide minimal failing example, together with information about the specific version of the package (ideally git commit), Python version, pyyaml version, libyaml version (if used), and OS used.


## License

The package is released under Apache License 2.0.
See LICENSE file for more information.
