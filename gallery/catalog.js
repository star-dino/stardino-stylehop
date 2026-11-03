// StyleHop Studio Catalog & Topic-to-Style Routing Matrix (`gallery/catalog.js`).
// Register each multi-scene style under `styles/<id>/` here so both the live studio
// and AI agents can select the best visual style & camera grammar for any user topic.
export const STYLES = [
  {
    id: 'clay-macaron',
    name: 'Clay Macaron',
    zh: '3D 马卡龙',
    scenes: 4,
    dur: 14.8,
    preset: 'clay',
    stageMode: '3d-pure',
    defaultOverlay: 'none',
    kernel: './kernel.js',
    bestFor: [
      '治愈故事 / 绘本童话 / 奇幻微缩世界',
      '甜品烘焙 / 咖啡茶饮 / 美食料理 / 节日礼盒开箱',
      '手作工艺 / 潮玩盲盒 / 角色小剧场 / 温馨日常',
      '物理机关 / 八音盒 / 多米诺骨牌 / 定格动画短片',
    ],
    avoidFor: [
      '高密度金融K线报表',
      '纯命令行代码终端演示',
    ],
    keywords: [
      '故事', '童话', '绘本', '甜品', '蛋糕', '马卡龙', '咖啡', '茶', '烘焙', '美食',
      '森林', '动物', '小熊', '兔子', '猫', '太空', '探险', '盲盒', '礼盒', '手作',
      '玩具', '八音盒', '微缩', '小镇', '温暖', '治愈', '定格', '黏土', '软陶', '动画',
      'clay', 'story', 'miniature', 'cute', 'cozy', 'stop-motion',
    ],
    cameraPresets: [
      'macroPush',
      'tabletopOrbit',
      'craneReveal',
      'streetTrack',
      'dollyVertigo',
      'finaleOrbit',
    ],
  },
  {
    id: 'ink-wash',
    name: 'Ink Wash Scroll',
    zh: '水墨丹青',
    scenes: 5,
    dur: 24.4,
    preset: 'ink',
    stageMode: '3d-pure',
    defaultOverlay: 'none',
    kernel: './kernel.js',
    bestFor: [
      '国风意境 / 古诗词可视化 / 山水画卷 / 东方美学叙事',
      '茶道咖啡 / 瓷器非遗 / 传统手作工艺 / 节气文化与东方好物',
      '武侠江湖 / 文人雅集 / 神话寓言 / 历史人物故事短片',
      '水墨花鸟 / 仙鹤锦鲤 / 哲理禅意 / 书法挥毫与解谜小剧场',
    ],
    avoidFor: [
      '高密度金融K线报表',
      '纯命令行代码终端演示',
    ],
    keywords: [
      '水墨', '国画', '国风', '丹青', '青绿', '千里江山', '宋代', '宣纸', '毛笔', '书法',
      '挥毫', '山水', '古诗', '诗词', '武侠', '江湖', '剑客', '竹林', '古琴', '抚琴',
      '茶道', '点茶', '煮茶', '泡茶', '龙井', '紫砂', '瓷器', '青花瓷', '汝窑', '非遗',
      '节气', '仙鹤', '白鹭', '锦鲤', '荷花', '墨荷', '梅花', '古亭', '泛舟', '扁舟',
      '印章', '朱砂', '太极', '禅意', '东方', 'ink', 'inkwash', 'calligraphy', 'chinese',
      'scroll', 'shanshui', 'wuxia', 'zen', 'porcelain',
    ],
    cameraPresets: [
      'macroPush',
      'widePull',
      'craneReveal',
      'lateralTrack',
      'finaleOrbit',
      'vertigoZoom',
    ],
  },
  {
    id: 'twilight-fable',
    name: 'Twilight Bioluminescent Fable',
    zh: '暮光柔焦绘本',
    scenes: 4,
    dur: 14.0,
    preset: 'twilight',
    stageMode: '3d-pure',
    defaultOverlay: 'none',
    kernel: './kernel.js',
    bestFor: [
      '治愈绘本童话 / 奇幻森林冒险 / 萌宠与自然生灵温情故事',
      '星空许愿 / 仲夏夜萤火 / 极光漫游 / 梦境与情绪疗愈短片',
      '香氛精油 / 睡眠助眠 / 茶饮花果 / 温暖灯光与家居美学',
      '音乐MV视觉 / 节气夜游 / 绘本风科普与诗意寓言',
    ],
    avoidFor: [
      '高密度现代金融K线与财务报表',
      '纯命令行代码终端演示',
      '长吻长腿写实动物（鹿/马）的面部特写与主角戏（尚无 sleek 体型；仅可作中远景 spirit 灵影）',
    ],
    keywords: [
      '暮光', '柔焦', '散景', '绘本', '星光', '星空', '萤火', '萤火虫', '蒲公英', '极光',
      '森林', '雾林', '树洞', '暖窗', '浅滩', '溪流', '水波', '倒影', '灵兽', '萌宠',
      '小猫', '小熊', '小狐狸', '耳廓狐', '长耳兔', '小鹿', '蘑菇', '发光', '荧光', '夜空',
      '梦境', '睡眠', '晚安', '助眠', '香氛', '治愈', '唯美', '温暖', '许愿', '星河', '童话',
      'twilight', 'fable', 'bokeh', 'bioluminescent', 'starlight', 'aurora', 'firefly',
      'dandelion', 'dreamy', 'healing', 'storybook', 'lullaby', 'critter', 'kitten', 'bear', 'fox', 'bunny',
    ],
    cameraPresets: [
      'macroPush',
      'widePull',
      'craneReveal',
      'lateralTrack',
      'finaleOrbit',
      'tabletopOrbit',
    ],
  },
  {
    id: 'vintage-naturalist',
    name: 'Vintage Naturalist',
    zh: '复古博物学',
    scenes: 4,
    dur: 15.0,
    preset: 'naturalist',
    stageMode: 'hybrid',
    defaultOverlay: 'typography',
    kernel: './kernel.js',
    bestFor: [
      '科学史 / 博物学 / 演化与自然选择 / 生物学机制拆解',
      '论文解读 / 顶刊成果 / 实验与证据链 / 辟谣与科学边界',
      '天文地质 / 古生物化石 / 标本档案 / 博物馆与田野笔记',
      '医学与神经科学 / 分子机制 / 工程原理 / 硬核知识科普',
    ],
    avoidFor: [
      '高密度金融K线与财务报表',
      '纯命令行代码终端演示',
      '无旁白的抽象情绪短片 / 纯氛围音乐可视化',
    ],
    keywords: [
      '科普', '博物', '博物学', '科学', '论文', '顶刊', '研究', '实验', '证据', '机制',
      '演化', '进化', '自然选择', '达尔文', '雀', '地雀', '喙', '标本', '化石', '古生物',
      '生物', '基因', '细胞', '分子', '医学', '神经', '大脑', '天文', '地质', '博物馆',
      '田野', '档案', '图版', '铜版画', '羊皮纸', '复古', '手稿', '辟谣', '硬核', '数据',
      'science', 'natural history', 'engraving', 'copperplate', 'parchment', 'specimen',
      'evolution', 'darwin', 'fossil', 'museum', 'explainer',
    ],
    cameraPresets: [
      'macroPush',
      'widePull',
      'craneReveal',
      'lateralTrack',
      'finalePull',
    ],
  },
  {
    id: 'calibration-lab',
    name: 'Calibration Lab',
    zh: '计量实验室',
    scenes: 4,
    dur: 16.0,
    preset: 'terminal',
    stageMode: '3d-pure',
    defaultOverlay: 'none',
    kernel: './kernel.js',
    bestFor: [
      '机械原理 / 结构拆解 / 剖视解释（发动机 / 泵 / 减速箱 / 连杆机构）',
      '工业产品与量具 / 标定与公差 / 制造工艺科普',
      '工程教学 / 物理机制讲解 / “它为什么这么动”',
      '技术发布会结构页 / 专利与论文机制可视化',
    ],
    avoidFor: [
      '需要情绪与角色的故事短片',
      '高密度金融K线与财务报表',
      '纯命令行代码终端演示',
    ],
    keywords: [
      '机械', '原理', '结构', '剖视', '剖面', '爆炸图', '拆解', '机构', '发动机', '引擎',
      '四冲程', '曲轴', '活塞', '连杆', '凸轮', '气门', '齿轮', '减速箱', '变速箱', '泵',
      '液压', '轴承', '公差', '标定', '量具', '实验室', '工程', '工业', '制造', '装配',
      '教学', '科普', '怎么工作', '为什么', '原理演示',
      'machine', 'mechanism', 'cutaway', 'section', 'exploded', 'engine', 'piston', 'crank',
      'gear', 'pump', 'bearing', 'calibration', 'metrology', 'engineering', 'assembly',
      'how it works', 'explainer',
    ],
    cameraPresets: [
      'heroEstablish',
      'macroPush',
      'tabletopOrbit',
      'dollyVertigo',
      'finalePull',
    ],
  },
];

export const SIZES = [
  { id: '1920x1080', name: '16:9 横屏' },
  { id: '1080x1920', name: '9:16 竖屏' },
  { id: '1080x1080', name: '1:1 方画幅' },
];

/**
 * Recommends the best-matching StyleHop style for a free-form user topic string by scoring
 * each style's `keywords`. Returns null when no style matches at all: check `avoidFor` and tell
 * the user the topic is outside the current styles rather than forcing one.
 */
export function selectStyleForTopic(topic = '') {
  const text = String(topic).toLowerCase();
  let best = null;
  let bestScore = 0;
  for (const s of STYLES) {
    const score = (s.keywords || []).reduce((n, kw) => n + (text.includes(kw) ? 1 : 0), 0);
    if (score > bestScore) {
      best = s;
      bestScore = score;
    }
  }
  return best;
}
