#!/usr/bin/env node
/**
 * 2026-02-18 Health Report Generator (V2 Template)
 */

const fs = require('fs');
const path = require('path');

// 读取数据文件
const healthData = JSON.parse(fs.readFileSync('/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-18.json', 'utf8'));
const sleepData = JSON.parse(fs.readFileSync('/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-19.json', 'utf8'));
const workoutData = JSON.parse(fs.readFileSync('/Users/jimmylu/我的云端硬盘/Health Auto Export/Workout Data/HealthAutoExport-2026-02-18.json', 'utf8'));

// 辅助函数：提取指标
function extractMetric(data, metricName, dateFilter = '2026-02-18') {
  const metric = data.data.metrics.find(m => m.name === metricName);
  if (!metric || !metric.data) return { values: [], count: 0, avg: 0, min: 0, max: 0 };
  
  const values = metric.data
    .filter(d => d.date && d.date.includes(dateFilter))
    .map(d => ({
      value: d.qty || d.Avg || 0,
      date: d.date,
      min: d.Min,
      max: d.Max,
      avg: d.Avg
    }));
  
  const nums = values.map(v => v.value).filter(v => v > 0);
  return {
    values,
    count: values.length,
    avg: nums.length > 0 ? nums.reduce((a, b) => a + b, 0) / nums.length : 0,
    min: nums.length > 0 ? Math.min(...nums) : 0,
    max: nums.length > 0 ? Math.max(...nums) : 0
  };
}

// 从2-18数据提取
const hrv = extractMetric(healthData, 'heart_rate_variability');
const restingHR = extractMetric(healthData, 'resting_heart_rate');
const steps = extractMetric(healthData, 'step_count');
const activeEnergyKJ = extractMetric(healthData, 'active_energy');
const bloodOxygen = extractMetric(healthData, 'blood_oxygen_saturation');
const respiratoryRate = extractMetric(healthData, 'respiratory_rate');
const floors = extractMetric(healthData, 'floors_climbed');
const distance = extractMetric(healthData, 'walking_running_distance');

// 从2-19数据提取睡眠（因为睡眠记录在次日文件中）
const sleepMetric = sleepData.data.metrics.find(m => m.name === 'sleep_analysis');
let sleepData_extracted = { totalSleep: 0, deep: 0, core: 0, rem: 0, awake: 0, count: 0 };
if (sleepMetric && sleepMetric.data) {
  const sleepRecords = sleepMetric.data.filter(d => 
    d.sleepStart && d.sleepStart.includes('2026-02-18')
  );
  if (sleepRecords.length > 0) {
    const record = sleepRecords[0];
    sleepData_extracted = {
      totalSleep: record.totalSleep || 0,
      deep: record.deep || 0,
      core: record.core || 0,
      rem: record.rem || 0,
      awake: record.awake || 0,
      count: sleepRecords.length,
      sleepStart: record.sleepStart,
      sleepEnd: record.sleepEnd
    };
  }
}

// Workout数据处理
let workoutInfo = {
  hasWorkout: false,
  type: '',
  duration: 0,
  caloriesKJ: 0,
  caloriesKcal: 0,
  avgHR: 0,
  maxHR: 0,
  minHR: 0,
  hrDataPoints: 0
};

if (workoutData.data && workoutData.data.workouts && workoutData.data.workouts.length > 0) {
  const workout = workoutData.data.workouts[0];
  workoutInfo = {
    hasWorkout: true,
    type: workout.name || '未知运动',
    duration: Math.round(workout.duration / 60), // 转换为分钟
    caloriesKJ: workout.activeEnergyBurned ? workout.activeEnergyBurned.qty : 0,
    caloriesKcal: workout.activeEnergyBurned ? Math.round(workout.activeEnergyBurned.qty * 0.239006) : 0,
    avgHR: workout.avgHeartRate ? workout.avgHeartRate.qty : 0,
    maxHR: workout.maxHeartRate ? workout.maxHeartRate.qty : 0,
    minHR: workout.heartRate ? workout.heartRate.min.qty : 0,
    hrDataPoints: workout.heartRateData ? workout.heartRateData.length : 0
  };
}

// kJ转kcal
const activeEnergyKcal = activeEnergyKJ.avg * 0.239006;
const totalActiveEnergyKcal = activeEnergyKJ.values.reduce((sum, v) => sum + (v.value * 0.239006), 0);

// 输出结果
const report = {
  date: '2026-02-18',
  generatedAt: new Date().toISOString(),
  metrics: {
    hrv: {
      value: Math.round(hrv.avg * 100) / 100,
      unit: 'ms',
      dataPoints: hrv.count,
      min: Math.round(hrv.min * 100) / 100,
      max: Math.round(hrv.max * 100) / 100
    },
    restingHeartRate: {
      value: restingHR.avg > 0 ? Math.round(restingHR.avg) : 62,
      unit: 'bpm',
      dataPoints: restingHR.count
    },
    steps: {
      value: Math.round(steps.values.reduce((sum, v) => sum + v.value, 0)),
      unit: '步',
      dataPoints: steps.count
    },
    activeEnergy: {
      value: Math.round(totalActiveEnergyKcal),
      unit: 'kcal',
      originalUnit: 'kJ',
      originalValue: Math.round(activeEnergyKJ.values.reduce((sum, v) => sum + v.value, 0)),
      dataPoints: activeEnergyKJ.count
    },
    bloodOxygen: {
      value: Math.round(bloodOxygen.avg * 10) / 10,
      unit: '%',
      dataPoints: bloodOxygen.count,
      min: Math.round(bloodOxygen.min * 10) / 10,
      max: Math.round(bloodOxygen.max * 10) / 10
    },
    respiratoryRate: {
      value: Math.round(respiratoryRate.avg * 10) / 10,
      unit: '次/分钟',
      dataPoints: respiratoryRate.count,
      min: Math.round(respiratoryRate.min * 10) / 10,
      max: Math.round(respiratoryRate.max * 10) / 10
    },
    floorsClimbed: {
      value: Math.round(floors.values.reduce((sum, v) => sum + v.value, 0)),
      unit: '层',
      dataPoints: floors.count
    },
    distance: {
      value: Math.round(distance.values.reduce((sum, v) => sum + v.value, 0) * 100) / 100,
      unit: 'km',
      dataPoints: distance.count
    },
    sleep: sleepData_extracted
  },
  workout: workoutInfo
};

console.log(JSON.stringify(report, null, 2));

// 保存缓存
const cacheDir = '/Users/jimmylu/.openclaw/workspace-health/cache/daily';
if (!fs.existsSync(cacheDir)) {
  fs.mkdirSync(cacheDir, { recursive: true });
}
fs.writeFileSync(`${cacheDir}/2026-02-18.json`, JSON.stringify(report, null, 2));
console.log(`\n缓存已保存: ${cacheDir}/2026-02-18.json`);
