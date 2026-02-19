# Google Fit API 配置教程

本教程将指导你如何创建 Google Cloud 项目，启用 Fitness API，并获取 OAuth 凭证。

## 准备工作

1. Google 账号
2. 可以访问 Google Cloud Console 的浏览器
3. 已安装 Health Auto Export 并同步数据到 Google Drive

## 步骤 1：创建 Google Cloud 项目

### 1.1 访问 Google Cloud Console

1. 打开浏览器，访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 登录你的 Google 账号

![Google Cloud Console](assets/tutorial/gcloud-home.png)

### 1.2 创建新项目

1. 点击页面顶部的 **项目选择器**（显示当前项目名称）
2. 在弹出窗口中点击 **"New Project"**（新项目）

![项目选择器](assets/tutorial/project-selector.png)

3. 填写项目信息：
   - **Project name**: `health-report`
   - **Location**: 选择你的组织（可选，个人用户留空）
   - **Billing account**: 选择你的结算账号

4. 点击 **"Create"** 创建项目

![创建项目](assets/tutorial/create-project.png)

5. 等待项目创建完成，然后点击 **"Select Project"** 切换到新项目

## 步骤 2：启用 Fitness API

### 2.1 进入 API 库

1. 点击左侧菜单 ☰ → **"APIs & Services"** → **"Library"**

![API 库](assets/tutorial/api-library.png)

### 2.2 搜索并启用 Fitness API

1. 在搜索框中输入 **"Fitness API"**
2. 点击 **"Fitness API"** 结果

![搜索 Fitness API](assets/tutorial/search-fitness-api.png)

3. 点击 **"Enable"**（启用）按钮

![启用 API](assets/tutorial/enable-api.png)

4. 等待 API 启用完成（约 10-30 秒）

## 步骤 3：配置 OAuth 同意屏幕

### 3.1 进入 OAuth 配置

1. 点击左侧菜单 ☰ → **"APIs & Services"** → **"OAuth consent screen"**

![OAuth 同意屏幕](assets/tutorial/oauth-consent.png)

### 3.2 选择用户类型

1. 选择 **"External"**（外部）- 适用于个人使用
2. 点击 **"Create"**

![用户类型](assets/tutorial/user-type.png)

### 3.3 填写应用信息

1. **App name**: `Health Report`
2. **User support email**: 选择你的邮箱
3. **Developer contact information**: 输入你的邮箱
4. 点击 **"Save and Continue"**

![应用信息](assets/tutorial/app-info.png)

### 3.4 配置范围（Scopes）

1. 点击 **"Add or Remove Scopes"**
2. 搜索并添加以下范围：
   - ✅ `.../auth/fitness.sleep.read` - 读取睡眠数据
   - ✅ `.../auth/fitness.activity.read` - 读取活动数据
3. 点击 **"Update"**
4. 点击 **"Save and Continue"**

![范围配置](assets/tutorial/scopes.png)

### 3.5 完成配置

1. 在 "Test users" 页面，点击 **"Add Users"**
2. 添加你的 Google 邮箱
3. 点击 **"Save and Continue"**
4. 最后点击 **"Back to Dashboard"**

## 步骤 4：创建 OAuth 凭证

### 4.1 进入凭证页面

1. 点击左侧菜单 ☰ → **"APIs & Services"** → **"Credentials"**

![凭证页面](assets/tutorial/credentials.png)

### 4.2 创建 OAuth Client ID

1. 点击 **"Create Credentials"** → **"OAuth client ID"**

![创建凭证](assets/tutorial/create-credentials.png)

2. 选择应用类型：**"Desktop app"**
3. 输入名称：`Health Report Desktop`
4. 点击 **"Create"**

![桌面应用](assets/tutorial/desktop-app.png)

### 4.3 下载凭证文件

1. 创建成功后，会显示 Client ID 和 Client Secret
2. 点击 **"Download JSON"** 按钮
3. 将文件保存为 `client_secret.json`
4. **⚠️ 重要：请妥善保管此文件，不要分享给他人**

![下载 JSON](assets/tutorial/download-json.png)

## 步骤 5：完成配置

### 5.1 运行配置脚本

在终端中运行：

```bash
./setup-google-fit.sh
```

或者在交互式安装中已经包含此步骤。

### 5.2 授权访问

1. 脚本会自动打开浏览器
2. 登录你的 Google 账号
3. 点击 "Allow" 授权访问 Fitness 数据
4. 授权成功后，终端会显示 "✅ Google Fit 授权成功！"

![授权页面](assets/tutorial/auth-page.png)

## 验证配置

运行以下命令验证配置是否成功：

```bash
python3 scripts/get_google_fit_sleep.py $(date +%Y-%m-%d)
```

如果显示睡眠数据，说明配置成功！

## 故障排除

### 问题："This app isn't verified"

**解决方法：**
1. 点击 "Advanced"
2. 点击 "Go to Health Report (unsafe)"
3. 继续授权流程

> ⚠️ 这是正常的，因为应用是你自己创建的，没有经过 Google 验证。

### 问题："Error 403: access_denied"

**解决方法：**
1. 确保你在 OAuth 同意屏幕中添加了测试用户
2. 确保使用的是同一个 Google 账号
3. 等待几分钟后重试

### 问题：无法下载 JSON 文件

**解决方法：**
1. 在 Credentials 页面点击你的 OAuth Client ID
2. 点击 "Download JSON" 按钮
3. 或者复制 Client ID 和 Client Secret 手动创建文件

## 下一步

完成 Google Fit API 配置后，运行：

```bash
./install.sh
```

完成整个系统的安装和配置。
