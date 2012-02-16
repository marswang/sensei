package com.senseidb.search.relevance;

import java.util.Set;

import com.browseengine.bobo.facets.data.MultiValueFacetDataCache;
import com.browseengine.bobo.facets.data.TermDoubleList;

public class MFacetDouble extends MFacet
{

  public MFacetDouble(MultiValueFacetDataCache mDataCaches)
  {
    super(mDataCaches);
  }

  @Override
  public boolean containsAll(Set set)
  {
    for(int i=0; i< this.length; i++)
      if(set.contains(((TermDoubleList) _mTermList).getPrimitiveValue(buf[i])))
        return true;
              
    return false;
  }

  public boolean containsAll(double[] target)
  {
    return false;
  }
  
  
  public boolean contains(double target)
  {
    for(int i=0; i< this.length; i++)
      if(((TermDoubleList) _mTermList).getPrimitiveValue(buf[i]) == target)
        return true;
              
    return false;
  }
  
}
