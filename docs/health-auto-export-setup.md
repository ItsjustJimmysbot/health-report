# Health Auto Export 配置教程

本教程将指导你如何在 iPhone 上配置 Health Auto Export，将 Apple Health 数据自动同步到 Google Drive。

## 准备工作

1. iPhone（iOS 14+）
2. Apple Watch（可选，但推荐）
3. 已登录的 Google 账号
4. 手机上已安装 Google Drive 应用

## 步骤 1：下载应用

1. 打开 App Store
2. 搜索 "Health Auto Export"
3. 下载并安装应用（开发者：Tweaking Technologies）

![App Store 搜索](assets/tutorial/app-store-search.png)

## 步骤 2：初始设置

1. 打开 Health Auto Export 应用
2. 首次启动时，点击 "Allow" 授权访问 Health 数据
3. 授予所有请求的权限：
   - 活动记录
   - 身体测量
   - 心率
   - 睡眠
   - 锻炼

![权限请求](assets/tutorial/permissions.png)

## 步骤 3：配置导出设置

### 3.1 进入设置

1. 点击右上角的 **⚙️ 设置图标**
2. 选择 **"Export Settings"**

![设置菜单](assets/tutorial/settings-menu.png)

### 3.2 选择导出格式

1. 找到 **"Export Format"** 选项
2. 选择 **"JSON"**
3. 确保 "Pretty Print" 选项为 **关闭**（节省空间）

![导出格式](assets/tutorial/export-format.png)

### 3.3 设置导出频率

1. 找到 **"Export Frequency"** 选项
2. 选择 **"Daily"**（每日）
3. 设置导出时间（建议：凌晨 2:00）

![导出频率](assets/tutorial/export-frequency.png)

### 3.4 选择导出数据

1. 点击 **"Select Data to Export"**
2. 勾选以下类别：
   - ✅ Activity (活动)
   - ✅ Body Measurements (身体测量)
   - ✅ Heart Rate (心率)
   - ✅ Sleep (睡眠)
   - ✅ Workouts (锻炼)

![数据选择](assets/tutorial/data-selection.png)

## 步骤 4：配置云同步

### 4.1 启用云同步

1. 返回设置主菜单
2. 找到 **"Cloud Sync"** 选项
3. 开启 **"Auto Sync to Cloud"**

![云同步](assets/tutorial/cloud-sync.png)

### 4.2 选择 Google Drive

1. 点击 **"Cloud Provider"**
2. 选择 **"Google Drive"**
3. 点击 "Sign in with Google"
4. 登录你的 Google 账号
5. 授予应用访问 Google Drive 的权限

![Google 登录](assets/tutorial/google-signin.png)

### 4.3 设置同步路径

1. 找到 **"Sync Folder"** 选项
2. 输入路径：**`Health Auto Export/`**
3. 确保勾选 "Create subfolders"（创建子文件夹）

![同步路径](assets/tutorial/sync-path.png)

## 步骤 5：验证配置

### 5.1 手动测试导出

1. 返回应用主界面
2. 点击底部的 **"Export Now"** 按钮
3. 等待导出完成（可能需要 1-2 分钟）
4. 检查是否显示 "Export Successful"

![导出成功](assets/tutorial/export-success.png)

### 5.2 检查 Google Drive

1. 打开 iPhone 上的 Google Drive 应用
2. 进入 "Health Auto Export" 文件夹
3. 确认看到以下子文件夹：
   - `Health Data/` - 包含 HealthAutoExport-YYYY-MM-DD.json
   - `Workout Data/` - 包含锻炼详细数据

![Google Drive 文件](assets/tutorial/drive-files.png)

### 5.3 检查 Mac 同步

1. 在 Mac 上打开 Finder
2. 进入 Google Drive 文件夹
3. 确认路径存在：`~/Library/CloudStorage/GoogleDrive-*/Health Auto Export/`

## 故障排除

### 问题：导出失败

**解决方法：**
1. 检查网络连接
2. 确保 Health 权限已授予
3. 尝试重新登录 Google 账号
4. 重启应用

### 问题：Google Drive 中没有文件

**解决方法：**
1. 检查 Google Drive 应用是否已登录
2. 确认云同步已启用
3. 手动点击 "Export Now" 测试
4. 检查 Google Drive 存储空间

### 问题：Mac 上没有同步

**解决方法：**
1. 确保 Mac 上已安装 Google Drive 桌面版
2. 检查 Google Drive 设置中的同步选项
3. 等待同步完成（首次同步可能需要较长时间）

## 下一步

完成 Health Auto Export 配置后，请继续配置 [Google Fit API](google-fit-setup.md)。
