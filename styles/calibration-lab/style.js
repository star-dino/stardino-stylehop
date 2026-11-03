export default {
  id: 'calibration-lab',
  name: 'Calibration Lab',
  zh: '计量实验室',
  description:
    'Pale seamless studio, anodized aluminium and engraved bench grid: a machine shown as a sample under measurement. Section cuts, staged explode and an instrument HUD whose numbers come from the same function that poses the parts.',
  stageMode: '3d-pure',
  defaultOverlay: 'none',
  kernel: './kernel.js',
  world: './world.js',
  soundPreset: 'industrial-mech',
  paperTexture: '../assets/textures/brushed_metal.png',
  bestFor: [
    '机械原理 / 结构拆解 / 剖视解释（发动机、泵、减速箱、连杆机构）',
    '工业产品与量具 / 标定与公差 / 制造工艺科普',
    '工程教学 / 物理机制讲解 / “它为什么这么动”',
    '技术发布会中的结构页 / 专利与论文机制可视化',
  ],
  avoidFor: [
    '需要情绪与角色的故事短片',
    '高密度金融 K 线与报表',
    '纯命令行代码终端演示',
  ],
  cameraPresets: [
    'heroEstablish',
    'macroPush',
    'tabletopOrbit',
    'dollyVertigo',
    'finalePull',
  ],
  // Screen-space finish only: the "dry instrument" grain. Material feel lives in the kernel
  // (anodized/steel/glass) and never as a screen-space texture.
  passes: [
    ['grain', { amount: 0.014, paper: 0.0, vignette: 0.16, warm: 0.0 }],
  ],
  look: {},
  layers: { tilt: 0.0, lift: 0, shadow: 0 },
};
