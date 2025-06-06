<div align=center>
<img  src="logo.png"/width="25%" height="25%">
</div>

<h1 align="center">
  <strong>People'sDailyEpubCreator</strong> ：用于从人民日报官方网站下载文章并生成EPUB电子书的python程序
</h1>

# 📌前言

## 免责声明

[People'sDailyEpubCreator](https://github.com/ARRray0-o/People-sDailyEpubCreator)作为一个开源项目在[GPL-3.0许可](https://github.com/ARRray0-o/People-sDailyEpubCreator?tab=GPL-3.0-1-ov-file)下发布，使用者可以在GPL-3.0许可的条款下自由地复制、分发和修改本程序。程序运行时会自动从[人民网](http://paper.people.com.cn/)获取指定日期的新闻内容，转换为EPUB格式的电子书，所有运行逻辑均可在源码中查看。《人民日报》（电子版）相关内容的[版权](#人民网官网版权声明)归人民网所有，受到版权法的保护。本程序的开发旨在为个人学习、研究或者新闻报道提供便利。在使用本程序时，应自行确保其行为符合相关版权法规，并尊重原始内容的版权。对于因使用本程序而可能引发的任何版权纠纷或法律责任，开发者不承担任何责任。

## 人民网官网版权声明

```
《人民日报》（电子版）的一切内容(包括但不限于文字、图片、PDF、图表、标志、标识、商标、版面设计、专栏目录与名称、内容分类标准以及为读者提供的任何信息)仅供人民网读者阅读、学习研究使用，未经人民网股份有限公司及/或相关权利人书面授权，任何单位及个人不得将《人民日报》（电子版）所登载、发布的内容用于商业性目的，包括但不限于转载、复制、发行、制作光盘、数据库、触摸展示等行为方式，或将之在非本站所属的服务器上作镜像。否则，人民网股份有限公司将采取包括但不限于网上公示、向有关部门举报、诉讼等一切合法手段，追究侵权者的法律责任。
```

## 注意

在且仅在Windows 10下测试运行成功。

此程序暂未成功获取文章内的图片，大约是个[三分之二成品](#未完成的功能)。

本程序绝大部分由AI人工智能构建，[ARRray](https://github.com/ARRray0-o)作为此仓库的发布者、使用者，对程序中代码一知半解。不规范欠考虑之处在所难免，欢迎开issue愉快讨论~

# 🎠开始使用

## 使用构建的应用程序(Windows)

直接在[release](https://github.com/ARRray0-o/People-sDailyEpubCreator/releases)中下载.exe文件后双击运行，输入规则见[用法](#用法)

## 使用python运行

### 确保python环境已安装

[百度:安装python环境](https://www.baidu.com/s?ch=3&ie=utf-8&wd=安装python环境)

### 安装依赖

```
pip install -r requirements.txt
```

### 运行python脚本

```
py People-sDailyEpubCreator.py
```

# 🛠功能
25-6-3更新内容

  •修复了2024.12.1官网改版后无法使用的问题

  •交互方式由命令行界面改为日历选择-按钮交互界面

自动从[人民日报官方网站](http://paper.people.com.cn/)获取指定日期的新闻文章，并转换成EPUB格式的电子书。程序会自动跳过重复的文章，以及在EPUB电子书中保留部分视觉元素。

## 特征

- 高兼容性.epub电子书(Windows第三方软件、iOS”图书“app、安卓系统自带/第三方阅读器均可正常阅读)
- 合并相同"版式"为一级目录，文章标题为二级目录，进度清晰可观，目录跳转流畅
- 文章内**加粗部分**还原
- …

## 未完成的功能

能力有限(╥﹏╥)无能为力

<details>
<summary><code>文章内嵌图片(及其下方注释)</code></summary>
    程序暂无法获取文章内的图片内容
——虽然加上图片会导致下载较慢、生成的文件体积较大，但部分图片内容展示了文章重要部分
——总之我可以不要但是不能没有 试了很多次都没成功
</details>
<details>
<summary><code>为电子书添加封面</code></summary>
    添加一张图片作为电子书封面不复杂，若在封面上加入日期信息就涉及到了代码处理图片 好麻烦(╥﹏╥)
</details>
<details>
<summary><code>云自动化</code></summary>
    目前python程序仅被成功打包为在Windows平台上易用的exe文件，云服务器每日自动运行发送至自己的邮箱应该不算复杂 但 还未配置成功(╥﹏╥)
</details>


…


# 🎉贡献

如果您对本项目感兴趣，非常欢迎在提交pr对[功能](#未完成的功能)进行完善。感谢您对项目的贡献！

# ✒后记

🏗建设中

## ✨欢迎点亮star~
