# QDII基金监控系统

这是一个自动监控LOF基金溢价率并发送企业微信通知的系统。

## 功能特点

- 实时爬取LOF基金数据
- 计算基金溢价率
- 对超过阈值的基金查询申购限额
- 通过企业微信发送通知
- 根据基金代码前缀显示"可拖"或"不拖"标识

## 配置说明

在 `config.ini` 文件中配置以下参数：

```ini
[WeChat]
webhook_url = https://qyapi.weixin.qq.com/cgi-bin/webhook/send
webhook_key = your_webhook_key

[FundAlert]
# 溢价率阈值，超过此值的基金会触发企业微信通知
premium_threshold = 5.0
```

## 定时执行

系统通过GitHub Actions每天自动执行，无需人工干预。