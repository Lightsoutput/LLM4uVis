// 从CSV文件加载地址链数据
export async function loadAddrChainData() {
    try {
        // 注意这里csv文件在public目录下！！！否则访问不到！！
      const response = await fetch('/SongData/SongAddrChain.csv');
      if (!response.ok) {
        throw new Error('网络响应错误: ' + response.statusText);
      }
      const csvData = await response.text();
      return parseCSV(csvData);
    } catch (error) {
      console.error('加载地址链数据失败:', error);
      return [];
    }
  }
  

// 解析CSV数据
function parseCSV(csvData) {
  const lines = csvData.trim().split('\n');
  const headers = lines[0].split(',');
  
  return lines.slice(1).map(line => {
    const values = line.split(',');
    const record = {};
    
    headers.forEach((header, index) => {
      record[header] = values[index];
    });
    
    return record;
  });
}

// 查找关键词在地址链中的记录
export function findAddressRecords(addrChainData, keywords) {
  if (!addrChainData || !keywords || keywords.length === 0) {
    return [];
  }
  
  // 将关键词转为小地点名集合
  const keywordSet = new Set(keywords.map(k => k.keyword || k));
  
  // 查找匹配的记录
  return addrChainData.filter(record => 
    keywordSet.has(record.Addr1) || 
    keywordSet.has(record.Addr2) || 
    keywordSet.has(record.Addr3)
  );
}

// 构建地址层次关系
export function buildAddressHierarchy(addrChainData, keywords) {
  // 查找相关记录
  const matchedRecords = findAddressRecords(addrChainData, keywords);
  
  if (matchedRecords.length === 0) {
    return { hierarchy: {}, smallToLarge: {} };
  }
  
  // 构建地点层次结构
  const hierarchy = {};
  const smallToLarge = {}; // 小地点到大地点的映射
  
  matchedRecords.forEach(record => {
    const { Addr1, Addr2, Addr3 } = record;
    
    // 添加到层次结构
    if (!hierarchy[Addr3]) {
      hierarchy[Addr3] = { name: Addr3, children: {} };
    }
    
    if (!hierarchy[Addr3].children[Addr2]) {
      hierarchy[Addr3].children[Addr2] = { name: Addr2, children: {} };
    }
    
    if (!hierarchy[Addr3].children[Addr2].children[Addr1]) {
      hierarchy[Addr3].children[Addr2].children[Addr1] = { name: Addr1 };
    }
    
    // 构建小地点到大地点的映射
    smallToLarge[Addr1] = { middle: Addr2, large: Addr3 };
    if (Addr2 !== Addr3) {
      smallToLarge[Addr2] = { large: Addr3 };
    }
  });
  
  return { hierarchy, smallToLarge };
}

// 准备LLM分析的提示词
export function prepareLocationPrompt(keywords, matchedRecords) {
  if (matchedRecords.length === 0) {
    return `分析以下地点之间可能的从属关系：${keywords.join('、')}`;
  }
  
  const prompt = `
  请分析以下地点之间的从属关系：${keywords.join('、')}
  
  已知的部分地址从属关系数据：
  ${matchedRecords.map(r => `${r.Addr1} 属于 ${r.Addr2} 属于 ${r.Addr3}`).join('\n')}
  
  请基于上述信息，分析这些地点之间的从属关系，并按照以下JSON格式返回结果：
  {
    "层次关系": [
      {
        "大地点": "省级地点名",
        "中级地点": [
          {
            "名称": "市级地点名",
            "包含": ["县级地点1", "县级地点2"]
          }
        ]
      }
    ]
  }
  
  只返回JSON格式的结果，不要有其他说明。
  `;
  
  return prompt;
} 