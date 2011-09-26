#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Python client library for Sensei
"""

import urllib
import urllib2
import json
import sys
import logging

# TODO:
#
# 1. Initializing runtime facet parameters
# 2. Partition Params

#
# REST API parameter constants
#
PARAM_OFFSET = "start"
PARAM_COUNT = "rows"
PARAM_QUERY = "q"
PARAM_QUERY_PARAM = "qparam"
PARAM_SORT = "sort"
PARAM_SORT_ASC = "asc"
PARAM_SORT_DESC = "desc"
PARAM_SORT_SCORE = "relevance"
PARAM_SORT_SCORE_REVERSE = "relrev"
PARAM_SORT_DOC = "doc"
PARAM_SORT_DOC_REVERSE = "docrev"
PARAM_FETCH_STORED = "fetchstored"
PARAM_SHOW_EXPLAIN = "showexplain"
PARAM_ROUTE_PARAM = "routeparam"
PARAM_SELECT = "select"
PARAM_SELECT_VAL = "val"
PARAM_SELECT_NOT = "not"
PARAM_SELECT_OP = "op"
PARAM_SELECT_OP_AND = "and"
PARAM_SELECT_OP_OR = "or"
PARAM_SELECT_PROP = "prop"
PARAM_FACET = "facet"
PARAM_DYNAMIC_INIT = "dyn"
PARAM_PARTITIONS = "partitions"

PARAM_FACET_EXPAND = "expand"
PARAM_FACET_MAX = "max"
PARAM_FACET_MINHIT = "minhit"
PARAM_FACET_ORDER = "order"
PARAM_FACET_ORDER_HITS = "hits"
PARAM_FACET_ORDER_VAL = "val"

PARAM_DYNAMIC_TYPE = "type"
PARAM_DYNAMIC_TYPE_STRING = "string"
PARAM_DYNAMIC_TYPE_BYTEARRAY = "bytearray"
PARAM_DYNAMIC_TYPE_BOOL = "boolean"
PARAM_DYNAMIC_TYPE_INT = "int"
PARAM_DYNAMIC_TYPE_LONG = "long"
PARAM_DYNAMIC_TYPE_DOUBLE = "double"
PARAM_DYNAMIC_VAL = "vals"

PARAM_RESULT_PARSEDQUERY = "parsedquery"
PARAM_RESULT_HIT_STORED_FIELDS = "stored"
PARAM_RESULT_HIT_STORED_FIELDS_NAME = "name"
PARAM_RESULT_HIT_STORED_FIELDS_VALUE = "val"
PARAM_RESULT_HIT_EXPLANATION = "explanation"
PARAM_RESULT_FACETS = "facets"

PARAM_RESULT_TID = "tid"
PARAM_RESULT_TOTALDOCS = "totaldocs"
PARAM_RESULT_NUMHITS = "numhits"
PARAM_RESULT_HITS = "hits"
PARAM_RESULT_HIT_UID = "uid"
PARAM_RESULT_HIT_DOCID = "docid"
PARAM_RESULT_HIT_SCORE = "score"
PARAM_RESULT_HIT_SRC_DATA = "srcdata"
PARAM_RESULT_TIME = "time"

PARAM_SYSINFO_NUMDOCS = "numdocs"
PARAM_SYSINFO_LASTMODIFIED = "lastmodified"
PARAM_SYSINFO_VERSION = "version"
PARAM_SYSINFO_FACETS = "facets"
PARAM_SYSINFO_FACETS_NAME = "name"
PARAM_SYSINFO_FACETS_RUNTIME = "runtime"
PARAM_SYSINFO_FACETS_PROPS = "props"
PARAM_SYSINFO_CLUSTERINFO = "clusterinfo"
PARAM_SYSINFO_CLUSTERINFO_ID = "id"
PARAM_SYSINFO_CLUSTERINFO_PARTITIONS = "partitions"
PARAM_SYSINFO_CLUSTERINFO_NODELINK = "nodelink"
PARAM_SYSINFO_CLUSTERINFO_ADMINLINK = "adminlink"

PARAM_RESULT_HITS_EXPL_VALUE = "value"
PARAM_RESULT_HITS_EXPL_DESC = "description"
PARAM_RESULT_HITS_EXPL_DETAILS = "details"

PARAM_RESULT_FACET_INFO_VALUE = "value"
PARAM_RESULT_FACET_INFO_COUNT = "count"
PARAM_RESULT_FACET_INFO_SELECTED = "selected"

#
# Definition of the SQL statement grammar
#

from pyparsing import Literal, CaselessLiteral, Word, Upcase, delimitedList, Optional, \
    Combine, Group, alphas, nums, alphanums, ParseException, Forward, oneOf, quotedString, \
    ZeroOrMore, restOfLine, Keyword

# SQL tokens

selectStmt   = Forward()
selectToken  = Keyword("select", caseless=True)
fromToken    = Keyword("from", caseless=True)
whereToken   = Keyword("where", caseless=True)
orderbyToken = Keyword("order by", caseless=True)
browseByToken = Keyword("browse by", caseless=True)
limitToken   = Keyword("limit", caseless=True)
queryToken   = Keyword("query", caseless=True)

ident          = Word(alphas, alphanums + "_$").setName("identifier")
columnName     = Word(alphas).setName("column")
columnNameList = Group(delimitedList(columnName))

whereExpression = Forward()
andToken        = Keyword("and", caseless=True)
inToken         = Keyword("in", caseless=True)
notInToken      = Keyword("not in", caseless=True)
isToken         = Keyword("is", caseless=True)
containsToken   = Keyword("contains", caseless=True)
notToken        = Keyword("not", caseless=True)
propToken       = Keyword("prop", caseless=True)

intNum = Word(nums)

selectOperation = oneOf("or and", caseless=True)

propPair = (quotedString + ":" + quotedString)

whereCondition = Group((columnName + ":" + selectOperation +
                        "(" + delimitedList(quotedString).setResultsName("value_list") + ")" +
                        Optional((notToken + "(" + delimitedList(quotedString).setResultsName("not_values") + ")")) +
                        Optional((propToken + "(" + delimitedList(propPair).setResultsName("prop_list") + ")"))
                        ) |
                       (queryToken + isToken + quotedString)
                       )
whereExpression << (whereCondition.setResultsName("condition", listAllMatches=True) +
                    ZeroOrMore(andToken + whereExpression))

orderseq    = oneOf("asc desc", caseless=True)
limitoffset = intNum
limitcount  = intNum

orderByExpression = Forward()
orderBySpec = Group(columnName + Optional(orderseq))
orderByExpression << (orderBySpec.setResultsName("orderby_spec", listAllMatches=True) +
                      ZeroOrMore("," + orderByExpression))

trueOrFalse = oneOf("true false", caseless=True)
facetOrderBy = oneOf("hits value", caseless=True)
facetSpec = Group(columnName + ":" + "(" + trueOrFalse + "," + intNum  + "," + intNum + "," + facetOrderBy + ")")
browseByExpression = "(" + delimitedList(facetSpec).setResultsName("facet_specs") + ")"

selectStmt << (selectToken + 
               ('*' | columnNameList).setResultsName("columns") + 
               fromToken + 
               ident.setResultsName("index") + 
               Optional((whereToken + whereExpression.setResultsName("where"))) +
               ZeroOrMore((orderbyToken + orderByExpression).setResultsName("orderby") |
                          (limitToken + Group(Optional(limitoffset + ",") + limitcount)).setResultsName("limit") |
                          (browseByToken + browseByExpression).setResultsName("browse_by")
                          ) +
               Optional(";")
               )

simpleSQL = selectStmt

# Define comment format, and ignore them
sqlComment = "--" + restOfLine
simpleSQL.ignore(sqlComment)

logger = logging.getLogger("sensei_client")

class SQLRequest:
  """A Sensei request with a SQL SELECT-like statement."""

  def __init__(self, sql_stmt):
    self.tokens = simpleSQL.parseString(sql_stmt, parseAll=True)
    self.query = ""
    self.selections = []

    where = self.tokens.where
    if where:
      for cond in where.condition:
        if cond[0] == "query" and cond[1] == "is":
          self.query = cond[2][1:-1]
        elif cond[1] == ":":
          operation = PARAM_SELECT_OP_OR
          if cond[2] == "and":
            operation = PARAM_SELECT_OP_AND
          select = SenseiSelection(cond[0], operation)
          for val in cond.value_list:
            select.addSelection(val[1:-1])
          for val in cond.not_values:
            select.addSelection(val[1:-1], True)
          for i in xrange(0, len(cond.prop_list), 3):
            select.addProperty(cond.prop_list[i][1:-1], cond.prop_list[i+2][1:-1])
          self.selections.append(select)

  def get_offset(self):
    """Get the offset (default 0)."""

    limit = self.tokens.limit
    if limit:
      if len(limit[1]) == 3:
        return int(limit[1][0])
      else:
        return 0
    else:
      return 0

  def get_count(self):
    """Get the count (default 10)."""

    limit = self.tokens.limit
    if limit:
      if len(limit[1]) == 3:
        return int(limit[1][2])
      else:
        return int(limit[1][0])
    else:
      return 10

  def get_index(self):
    """Get the index (i.e. table) name."""

    return self.tokens.index

  def get_columns(self):
    """Get the list of selected columns."""

    return self.tokens.columns

  def get_query(self):
    """Get the query string."""

    return self.query

  def get_sorts(self):
    """Get the SenseiSort array base on ORDER BY."""

    orderby = self.tokens.orderby
    if not orderby:
      return []
    else:
      orderby_spec = orderby.orderby_spec
      sorts = []
      for spec in orderby_spec:
        if len(spec) == 1:
          sorts.append(SenseiSort(spec[0]))
        else:
          sorts.append(SenseiSort(spec[0], spec[1] == "desc" and True or False))
      return sorts

  def get_selections(self):
    """Get all the selections from in statement."""

    return self.selections

  def get_facets(self):
    """Get facet specs."""

    facets = {}
    browse_by = self.tokens.browse_by
    if not browse_by:
      return facets
    facet_specs = browse_by.facet_specs
    for spec in facet_specs:
      facet = SenseiFacet(spec[3] == "true" and True or False,
                          int(spec[5]),
                          int(spec[7]),
                          spec[9] == "hits" and PARAM_FACET_ORDER_HITS or PARAM_FACET_ORDER_VAL)
      facets[spec[0]] = facet
    return facets


def test(str):
  # print str,"->"
  try:
    tokens = simpleSQL.parseString(str)
    print "tokens = ",        tokens
    print "tokens.columns =", tokens.columns
    print "tokens.index =",  tokens.index
    print "tokens.where =", tokens.where

    print "tokens.where = ", tokens.where
    if tokens.where:
      print "tokens.where.condition = ", tokens.where.condition
      for cond in tokens.where.condition:
        print "cond.value_list = ", cond.value_list
        print "cond.not_values = ", cond.not_values
        print "cond.prop_list = ", cond.prop_list
    print "tokens.orderby = ", tokens.orderby
    if tokens.orderby:
      print "tokens.orderby.orderby_spec = ", tokens.orderby.orderby_spec
    print "tokens.limit = ", tokens.limit
    print "tokens.browse_by = ", tokens.browse_by
    if tokens.browse_by:
      print "tokens.browse_by.facet_specs = ", tokens.browse_by.facet_specs
  except ParseException, err:
    print " "*err.loc + "^\n" + err.msg
    # print err
  print

def test_sql(stmt):
  # test(stmt)
  client = SenseiClient()
  req = SenseiRequest(stmt)
  res = client.doQuery(req)
  res.display(req.get_columns())


class SenseiClientError(Exception):
  """Exception raised for all errors related to Sensei client."""

  def __init__(self, value):
    self.value = value

  def __str__(self):
    return repr(self.value)


class SenseiFacet:
  def __init__(self,expand=False,minHits=1,maxCounts=10,orderBy=PARAM_RESULT_HITS):
    self.expand = expand
    self.minHits = minHits
    self.maxCounts = maxCounts
    self.orderBy = orderBy

class SenseiSelection:
  def __init__(self, field, operation=PARAM_SELECT_OP_OR):
    self.field = field
    self.operation = operation
    self.values = []
    self.excludes = []
    self.properties = {}

  def __str__(self):
    return ("Selection:%s:%s:%s:%s" %
            (self.field, self.operation,
             ','.join(self.values), ','.join(self.excludes)))
    
  def addSelection(self, value, isNot=False):
    if isNot:
      self.excludes.append(value)
    else:
      self.values.append(value)
  
  def removeSelection(self, value, isNot=False):
    if isNot:
      self.excludes.remove(value)
    else:
      self.values.remove(value)
  
  def addProperty(self, name, value):
    self.properties[name] = value
  
  def removeProperty(self, name):
    del self.properties[name]

  def getSelectNotParam(self):
    return "%s.%s.%s" % (PARAM_SELECT, self.field, PARAM_SELECT_NOT)

  def getSelectNotParamValues(self):
    return ",".join(self.excludes)

  def getSelectOpParam(self):
    return "%s.%s.%s" % (PARAM_SELECT, self.field, PARAM_SELECT_OP)

  def getSelectValParam(self):
    return "%s.%s.%s" % (PARAM_SELECT, self.field, PARAM_SELECT_VAL)

  def getSelectValParamValues(self):
    return ",".join(self.values)

  def getSelectPropParam(self):
    return "%s.%s.%s" % (PARAM_SELECT, self.field, PARAM_SELECT_PROP)

  def getSelectPropParamValues(self):
    return ",".join(key + ":" + self.properties.get(key)
        for key in self.properties.keys())
  

class SenseiSort:
  def __init__(self, field, reverse=False):
    self.field = field
    if not (field == PARAM_SORT_SCORE or
            field == PARAM_SORT_SCORE_REVERSE or
            field == PARAM_SORT_DOC or
            field == PARAM_SORT_DOC_REVERSE):
      if reverse:
        self.dir = PARAM_SORT_DESC
      else:
        self.dir = PARAM_SORT_ASC

  def __str__(self):
    return "%s:%s" % (self.field, self.dir)

  def buildSortField(self):
    if self.dir == "":
      return self.field
    else:
      return self.field + ":" + self.dir


class SenseiRequest:
  def __init__(self):
    self.facets = {}
    self.selections = []
    self.sorts = None
    self.query = None
    self.qParam = {}
    self.offset = 0
    self.count = 10
    self.explain = False
    self.fetch = False
    self.routeParam = None
    self.columns = []

  def __init__(self, sql_stmt):
    """Construct a Sensei request using a SQL SELECT-like statement."""

    self.facets = {}
    self.qParam = {}
    self.explain = False
    self.fetch = False
    self.routeParam = None

    sql_req = SQLRequest(sql_stmt)
    self.query = sql_req.get_query()
    self.offset = sql_req.get_offset()
    self.count = sql_req.get_count()
    self.columns = sql_req.get_columns()
    self.sorts = sql_req.get_sorts()
    self.selections = sql_req.get_selections()
    self.facets = sql_req.get_facets()

  def get_columns(self):
    return self.columns
  
# XXX Do we really need this class?
class SenseiHit:
  def __init__(self):
    self.docid = None
    self.uid = None
    self.srcData = {}
    self.score = None
    self.explanation = None
    self.stored = None
  
  def load(self, jsonHit):
    self.docid = jsonHit.get(PARAM_RESULT_HIT_DOCID)
    self.uid = jsonHit.get(PARAM_RESULT_HIT_UID)
    self.score = jsonHit.get(PARAM_RESULT_HIT_SCORE)
    srcStr = jsonHit.get(PARAM_RESULT_HIT_SRC_DATA)
    self.explanation = jsonHit.get(PARAM_RESULT_HIT_EXPLANATION)
    self.stored = jsonHit.get(PARAM_RESULT_HIT_STORED_FIELDS)
    if srcStr:
      self.srcData = json.loads(srcStr)
    else:
      self.srcData = None
  

class SenseiResultFacet:
  value = None
  count = None
  selected = None
  
  def load(self,json):
    self.value=json.get(PARAM_RESULT_FACET_INFO_VALUE)
    self.count=json.get(PARAM_RESULT_FACET_INFO_COUNT)
    self.selected=json.get(PARAM_RESULT_FACET_INFO_SELECTED,False)

  
class SenseiResult:
  """Sensei search results for a query."""

  MAX_LEN = 40

  def __init__(self, jsonData):
    self.jsonMap = jsonData
    self.parsedQuery = jsonData.get(PARAM_RESULT_PARSEDQUERY)
    self.totalDocs = jsonData.get(PARAM_RESULT_TOTALDOCS,0)
    self.time = jsonData.get(PARAM_RESULT_TIME,0)
    self.numHits = jsonData.get(PARAM_RESULT_NUMHITS,0)
    self.hits = jsonData.get(PARAM_RESULT_HITS)
    map = jsonData.get(PARAM_RESULT_FACETS)
    self.facetMap = {}
    if map:
      for k,v in map.items():
        facetList = []
        for facet in v:
          facetObj = SenseiResultFacet()
          facetObj.load(facet)
          facetList.append(facetObj)
        self.facetMap[k]=facetList

  def display(self, columns=['*']):
    """Print the results in SQL SELECT result format."""

    if not self.hits:
      print "No hit is found."
      return
    elif not columns:
      print "No column is selected."
      return

    keys = []
    if len(columns) == 1 and columns[0] == '*':
      keys = self.hits[0].keys()
    else:
      keys = columns

    max_lens = {}
    for key in keys:
      max_lens[key] = len(key)
    for hit in self.hits:
      for key in keys:
        if hit.has_key(key):
          v = hit.get(key)
        else:
          v = '<Not Found>'
        if isinstance(v, list):
          v = ','.join(v)
        elif isinstance(v, int):
          v = str(v)
        value_len = len(v)
        if value_len > max_lens[key]:
          max_lens[key] = min(value_len, self.MAX_LEN)
    # Print the result header
    sys.stdout.write('+')
    for key in keys:
      sys.stdout.write('-' * (max_lens[key] + 2) + '+')
    sys.stdout.write('\n|')
    for key in keys:
      sys.stdout.write(' %s%s |' % (key, ' ' * (max_lens[key] - len(key))))
    sys.stdout.write('\n+')
    for key in keys:
      sys.stdout.write('-' * (max_lens[key] + 2) + '+')
    # Print the results
    for hit in self.hits:
      sys.stdout.write('\n|')
      for key in keys:
        if hit.has_key(key):
          v = hit.get(key)
        else:
          v = '<Not Found>'
        if isinstance(v, list):
          v = ','.join(v)
        elif isinstance(v, int):
          v = str(v)
        if len(v) > self.MAX_LEN:
          v = v[:self.MAX_LEN]
        sys.stdout.write(' %s%s |' % (v, ' ' * (max_lens[key] - len(v))))
    # Print the result footer
    sys.stdout.write('\n+')
    for key in keys:
      sys.stdout.write('-' * (max_lens[key] + 2) + '+')
    sys.stdout.write('\n')
    sys.stdout.write('%s rows in set, %s hits, %s total docs\n' %
                     (len(self.hits), self.numHits, self.totalDocs))

    # Print facet information
    for facet, values in self.jsonMap.get(PARAM_RESULT_FACETS).iteritems():
      max_val_len = len(facet)
      max_count_len = 1
      for val in values:
        max_val_len = max(max_val_len, min(self.MAX_LEN, len(val.get('value'))))
        max_count_len = max(max_count_len, len(str(val.get('count'))))
      total_len = max_val_len + 2 + max_count_len + 3

      sys.stdout.write('+' + '-' * total_len + '+\n')
      sys.stdout.write('| ' + facet + ' ' * (total_len - len(facet) - 1) + '|\n')
      sys.stdout.write('+' + '-' * total_len + '+\n')

      for val in values:
        sys.stdout.write('| %s%s (%s)%s |\n' %
                         (val.get('value'),
                          ' ' * (max_val_len - len(val.get('value'))),
                          val.get('count'),
                          ' ' * (max_count_len - len(str(val.get('count'))))))
      sys.stdout.write('+' + '-' * total_len + '+\n')
  
class SenseiClient:
  """Sensei client class."""

  def __init__(self,host='localhost',port=8080,path='sensei'):
    self.host = host
    self.port = port
    self.path = path
    self.url = 'http://%s:%d/%s' % (self.host,self.port,self.path)
    self.opener = urllib2.build_opener()
    self.opener.addheaders = [('User-agent', 'Python-urllib/2.5')]
    self.opener.addheaders = [('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_7) AppleWebKit/534.30 (KHTML, like Gecko) Chrome/12.0.742.91 Safari/534.30')]
    
  @staticmethod
  def buildUrlString(req):
    paramMap = {}
    paramMap[PARAM_OFFSET] = req.offset
    paramMap[PARAM_COUNT] = req.count
    if req.query:
      paramMap[PARAM_QUERY]=req.query
    if req.explain:
      paramMap[PARAM_SHOW_EXPLAIN] = "true"
    if req.fetch:
      paramMap[PARAM_FETCH_STORED] = "true"
    if req.routeParam:
      paramMap[PARAM_ROUTE_PARAM] = req.routeParam

    # paramMap["offset"] = req.offset
    # paramMap["count"] = req.count

    if req.sorts:
      paramMap[PARAM_SORT] = ",".join(sort.buildSortField() for sort in req.sorts)

    if req.qParam.get("query"):
      paramMap[PARAM_QUERY] = req.qParam.get("query")
    paramMap[PARAM_QUERY_PARAM] = ",".join(param + ":" + req.qParam.get(param)
                                           for param in req.qParam.keys() if param != "query")

    for selection in req.selections:
      paramMap[selection.getSelectNotParam()] = selection.getSelectNotParamValues()
      paramMap[selection.getSelectOpParam()] = selection.operation
      paramMap[selection.getSelectValParam()] = selection.getSelectValParamValues()
      if selection.properties:
        paramMap[selection.getSelectPropParam()] = selection.getSelectPropParamValues()

    for facetName, facetSpec in req.facets.iteritems():
      paramMap["%s.%s.%s" % (PARAM_FACET, facetName, PARAM_FACET_MAX)] = facetSpec.maxCounts
      paramMap["%s.%s.%s" % (PARAM_FACET, facetName, PARAM_FACET_ORDER)] = facetSpec.orderBy
      paramMap["%s.%s.%s" % (PARAM_FACET, facetName, PARAM_FACET_EXPAND)] = facetSpec.expand
      paramMap["%s.%s.%s" % (PARAM_FACET, facetName, PARAM_FACET_MINHIT)] = facetSpec.minHits

    return urllib.urlencode(paramMap)
    
  def doQuery(self, req=None):
    paramString = None
    if req:
      paramString = SenseiClient.buildUrlString(req)
    logger.debug(paramString)
    urlReq = urllib2.Request(self.url,paramString)
    res = self.opener.open(urlReq)
    line = res.read()
    jsonObj = json.loads(line)
    res = SenseiResult(jsonObj)
    return res

def test_basic():
  print "==== Testing basic ====" 
  req = SenseiRequest()
  req.offset = 0
  req.count = 4

  client = SenseiClient()
  res = client.doQuery(req)
  print res.jsonMap


def testSort1():
  print "==== Testing sort1 ====" 
  req = SenseiRequest()
  req.offset = 0
  req.count = 4

  sort1 = SenseiSort("relevance")
  req.sorts = [sort1]
  
  client = SenseiClient()
  client.doQuery(req)

# XXX Sort on multiple columns Does NOT work yet
def testSort2():
  print "==== Testing sort2 ====" 
  req = SenseiRequest()
  req.offset = 0
  req.count = 4

  sort1 = SenseiSort("year", True)
  sort2 = SenseiSort("relevance")
  req.sorts = [sort1, sort2]
  
  client = SenseiClient()
  client.doQuery(req)


def testQueryParam():
  print "==== Testing query params ====" 
  req = SenseiRequest()
  req.offset = 0
  req.count = 4

  sort1 = SenseiSort("relevance")
  req.sorts = [sort1]

  qParam = {}
  qParam["query"] = "cool car"
  qParam["param1"] = "value1"
  qParam["param2"] = "value2"
  req.qParam = qParam
  
  client = SenseiClient()
  client.doQuery(req)

def testSelection():
  print "==== Testing selections ====" 
  req = SenseiRequest()
  req.offset = 0
  req.count = 3

  select1 = SenseiSelection("color", "or")
  select1.addSelection("red")
  select1.addSelection("yellow")
  select1.addSelection("black", True)
  select1.addProperty("aaa", "111")
  select1.addProperty("bbb", "222")

  select2 = SenseiSelection("price")
  select2.addSelection("[* TO 6700]")
  select2.addSelection("[10000 TO 13100]")
  select2.addSelection("[13200 TO 17300]")

  req.selections = [select1]
  client = SenseiClient()
  res = client.doQuery(req)
  print res.jsonMap

def testFacetSpecs():
  print "==== Testing facet specs ====" 
  req = SenseiRequest()
  req.query = 'moon-roof'
  req.offset = 0
  req.count = 10

  facet1 = SenseiFacet()
  facet2 = SenseiFacet(True, 1, 3, PARAM_FACET_ORDER_VAL)
  facet3 = SenseiFacet(True, 1, 3, PARAM_FACET_ORDER_VAL)

  req.facets["year"] = facet1
  req.facets["color"] = facet2
  req.facets["price"] = facet3
  req.facets["city"] = facet3
  req.facets["category"] = facet3

  sort = SenseiSort("price")
  req.sorts = [sort]
  
  client = SenseiClient()
  res = client.doQuery(req)
  # res.display()
  res.display(['year', 'color', 'tags', 'price'])
  # res.display(['bad_name'])

def main():
  logger.setLevel(logging.DEBUG)
  formatter = logging.Formatter("%(asctime)s %(filename)s:%(lineno)d - %(message)s")
  stream_handler = logging.StreamHandler()
  stream_handler.setFormatter(formatter)
  logger.addHandler(stream_handler)

  import readline
  readline.parse_and_bind("tab: complete")
  while 1:
    try:
      stmt = raw_input('> ')
      if stmt == "exit":
        break
      test_sql(stmt)
    except EOFError:
      print
      break
    except ParseException as err:
      print " "*err.loc + "^\n" + err.msg
      # print err

if __name__ == "__main__":

  main()

  # test_sql()

  # testFacetSpecs()
  # test_basic()
  # testSort1()
  # testQueryParam()
  # testSelection()

"""
Testing Data:

select color, year,tags, price from cars where query is "cool" and color: OR("gold", "green", "blue") NOT("black", "blue", "yellow", "white", "red", "silver") and year: OR("[1996 TO 1997]", "[2002 TO 2003]") order by price desc limit 0,10
+-------+----------------------+----------------------------------+-------------------------+
| color | year                 | tags                             | price                   |
+-------+----------------------+----------------------------------+-------------------------+
| gold  | 00000000000000001997 | cool,moon-roof,reliable,towing   | 00000000000000015000.00 |
| green | 00000000000000001996 | cool,favorite,reliable,towing    | 00000000000000015000.00 |
| green | 00000000000000001996 | cool,favorite,reliable,towing    | 00000000000000014800.00 |
| green | 00000000000000001996 | cool,moon-roof,reliable,towing   | 00000000000000014800.00 |
| green | 00000000000000002002 | automatic,cool,reliable,towing   | 00000000000000014800.00 |
| gold  | 00000000000000002002 | cool,favorite,navigation,towing  | 00000000000000014700.00 |
| gold  | 00000000000000001996 | cool,favorite,reliable,towing    | 00000000000000014700.00 |
| gold  | 00000000000000001997 | cool,favorite,reliable,towing    | 00000000000000014700.00 |
| gold  | 00000000000000001996 | cool,electric,moon-roof,reliable | 00000000000000014400.00 |
| gold  | 00000000000000001997 | cool,favorite,hybrid,reliable    | 00000000000000014200.00 |
+-------+----------------------+----------------------------------+-------------------------+
10 rows in set, 325 hits, 15001 total docs

select color, year,tags, price from cars where query is "cool" and tags: AND("cool", "hybrid") NOT("favorite") and color: OR("red", "yellow") order by price desc limit 0,5
+--------+----------------------+----------------------------------+-------------------------+
| color  | year                 | tags                             | price                   |
+--------+----------------------+----------------------------------+-------------------------+
| yellow | 00000000000000001995 | cool,hybrid,moon-roof,reliable   | 00000000000000014500.00 |
| red    | 00000000000000002000 | cool,hybrid,moon-roof,navigation | 00000000000000014500.00 |
| red    | 00000000000000001993 | cool,hybrid,moon-roof,navigation | 00000000000000014400.00 |
| red    | 00000000000000002002 | automatic,cool,hybrid,navigation | 00000000000000014200.00 |
| yellow | 00000000000000001999 | automatic,cool,hybrid,reliable   | 00000000000000012200.00 |
+--------+----------------------+----------------------------------+-------------------------+
5 rows in set, 132 hits, 15001 total docs

select color, year,tags, price from cars where query is "cool" and tags: and("cool", "hybrid") not("favorite") and color: and("red")  prop("aaa":"111", "bbb":"222") order by price desc limit 0,10 browse by (color: (true, 1, 10, hits), year: (true, 1, 10, value), price: (true, 1, 10, value))
+-------+----------------------+----------------------------------+-------------------------+
| color | year                 | tags                             | price                   |
+-------+----------------------+----------------------------------+-------------------------+
| red   | 00000000000000002000 | cool,hybrid,moon-roof,navigation | 00000000000000014500.00 |
| red   | 00000000000000001993 | cool,hybrid,moon-roof,navigation | 00000000000000014400.00 |
| red   | 00000000000000002002 | automatic,cool,hybrid,navigation | 00000000000000014200.00 |
| red   | 00000000000000001998 | automatic,cool,hybrid,navigation | 00000000000000012100.00 |
| red   | 00000000000000002002 | automatic,cool,hybrid,reliable   | 00000000000000011500.00 |
| red   | 00000000000000002002 | automatic,cool,hybrid,reliable   | 00000000000000011400.00 |
| red   | 00000000000000001998 | automatic,cool,hybrid,reliable   | 00000000000000011400.00 |
| red   | 00000000000000001996 | automatic,cool,hybrid,reliable   | 00000000000000011200.00 |
| red   | 00000000000000001999 | automatic,cool,hybrid,reliable   | 00000000000000011100.00 |
| red   | 00000000000000002001 | cool,hybrid,moon-roof,reliable   | 00000000000000010500.00 |
+-------+----------------------+----------------------------------+-------------------------+
10 rows in set, 59 hits, 15001 total docs
+-------------+
| color       |
+-------------+
| white  (73) |
| yellow (73) |
| blue   (62) |
| silver (61) |
| red    (59) |
| green  (58) |
| gold   (53) |
| black  (52) |
+-------------+
+-----------------------+
| price                 |
+-----------------------+
| [* TO 6700]      (21) |
| [10000 TO 13100] (8)  |
| [13200 TO 17300] (3)  |
| [6800 TO 9900]   (27) |
+-----------------------+
+---------------------+
| year                |
+---------------------+
| [1993 TO 1994] (16) |
| [1995 TO 1996] (13) |
| [1997 TO 1998] (10) |
| [1999 TO 2000] (9)  |
| [2001 TO 2002] (11) |
+---------------------+

"""
