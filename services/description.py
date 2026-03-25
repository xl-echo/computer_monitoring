#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/description.py
行为描述生成器 —— 将连接数据转换为通俗中文描述
（纯函数，无状态，可独立测试）
"""

from typing import Tuple


def build_plain_description(d: dict) -> str:
    """生成一句话通俗解读，面向非技术用户"""
    app = d.get("app_name", d.get("process_name", "某程序"))
    rip = d.get("remote_ip", "")
    rport = d.get("remote_port", 0)
    cat = d.get("category", "")
    direction = d.get("direction", "outbound")
    target = d.get("target", "")

    if rip.startswith("127.") or rip == "::1" or rip.startswith("169.254"):
        return "{}在本机内部通信，属于正常行为".format(app)

    if cat == "通讯":
        if direction == "outbound":
            return "{}正在向服务器发送数据（消息/心跳），目标服务器 {}".format(app, rip)
        return "{}正在从服务器接收数据（新消息推送），来源 {}".format(app, rip)

    if cat == "浏览器":
        return "浏览器正在加载网页，连接到 {}".format(target or rip)

    if cat == "邮件":
        if rport in (25, 465, 587):
            return "{}正在发送邮件，连接邮件服务器 {}".format(app, rip)
        return "{}正在收取邮件，从服务器 {} 下载".format(app, rip)

    if cat == "下载":
        return "{}正在进行文件下载/上传（P2P），连接节点 {}".format(app, rip)

    if cat == "远程":
        if direction == "outbound":
            return "{}正在连接远程电脑 {}，请确认是您主动操作的".format(app, rip)
        return "外部主机 {} 通过{}尝试访问本机，请确认是否授权".format(rip, app)

    if cat == "系统":
        return "Windows系统服务进行网络通信，通常为系统更新、时间同步等正常操作"

    if rport == 443:
        return "{}通过HTTPS加密通道连接 {}，数据已加密".format(app, rip)
    if rport == 80:
        return "{}通过HTTP明文连接 {}，注意：此连接未加密".format(app, rip)
    if rport == 3389:
        return "检测到RDP远程桌面连接！目标 {}，请确认是否为您主动操作".format(rip)

    if direction == "outbound":
        return "{}向外部服务器 {} 发起网络连接（端口 {}）".format(app, rip, rport)
    return "外部地址 {} 向本机发送数据，由{}处理".format(rip, app)


def build_friendly_action(d: dict) -> str:
    """将技术性 action_type 转换为通俗动作说明"""
    app = d.get("app_name", d.get("process_name", "某程序"))
    action = d.get("action_type", "")
    rip = d.get("remote_ip", "")
    rport = d.get("remote_port", 0)
    target = d.get("target", rip)

    mapping = {
        "发送消息":   "{}正在向对方发送消息".format(app),
        "接收消息":   "{}收到了新消息".format(app),
        "双向通讯":   "{}和服务器双向交换数据（发消息+收回复）".format(app),
        "连接服务器": "{}正在连接服务器，保持在线状态".format(app),
        "访问网站":   "浏览器正在打开网页：{}".format(target),
        "网站响应":   "网页服务器把内容返回给浏览器",
        "发送邮件":   "{}正在发出一封邮件".format(app),
        "接收邮件":   "{}正在收取新邮件".format(app),
        "邮件通讯":   "{}正在和邮件服务器通信".format(app),
        "下载文件":   "{}正在下载文件".format(app),
        "上传文件":   "{}正在上传文件".format(app),
        "P2P连接":    "{}通过P2P网络传输数据（类似共享下载）".format(app),
        "远程连接":   "{}正在远程控制另一台电脑：{}".format(app, rip),
        "远程访问":   "外部电脑{}正通过{}连接到您的电脑！".format(rip, app),
        "游戏连接":   "{}正在连接游戏服务器".format(app),
        "发送数据":   "{}向服务器发送了数据".format(app),
        "接收数据":   "{}从服务器接收了数据".format(app),
        "连接":       "{}建立了网络连接（端口{}）".format(app, rport),
    }
    return mapping.get(action, "{}正在进行网络通信".format(app))


def build_params_description(d: dict) -> Tuple[str, str]:
    """
    根据连接元数据生成通俗的请求/响应描述。
    返回 (请求描述, 响应描述)
    """
    rip = d.get("remote_ip", "")
    rport = d.get("remote_port", 0)
    app = d.get("app_name", d.get("process_name", ""))
    direction = d.get("direction", "outbound")
    cat = d.get("category", "")

    # 请求描述
    if direction == "outbound":
        if cat == "通讯":
            req = "{}向服务器{}:{}发起连接请求，询问是否有新消息或发送数据".format(app, rip, rport)
        elif cat == "浏览器":
            req = "浏览器向网站服务器发送「请给我这个页面」的请求"
        elif cat == "邮件":
            if rport in (25, 465, 587):
                req = "邮件程序向邮件服务器发送「请帮我发出这封邮件」的指令"
            else:
                req = "邮件程序向邮件服务器询问「有没有新邮件？」"
        elif cat == "下载":
            req = "下载程序向远端发送「我要下载/上传数据」的请求"
        elif cat == "远程":
            req = "远程工具向目标电脑{}发起「请求连接」的指令".format(rip)
        elif cat == "游戏":
            req = "游戏客户端向游戏服务器发送玩家操作数据"
        else:
            req = "{}向{}:{}发送了网络请求".format(app, rip, rport)
    else:
        req = "外部地址{}:{}主动向本机发来数据".format(rip, rport)

    # 响应描述
    if direction == "outbound":
        if cat == "通讯":
            resp = "服务器回复：连接成功，并推送最新消息或确认收到"
        elif cat == "浏览器":
            resp = "网站服务器返回网页内容（HTML/图片/视频等）给浏览器显示"
        elif cat == "邮件":
            if rport in (25, 465, 587):
                resp = "邮件服务器回复：邮件已成功发出"
            else:
                resp = "邮件服务器返回新邮件内容"
        elif cat == "下载":
            resp = "远端节点返回文件数据片段"
        elif cat == "远程":
            resp = "远程电脑接受连接，开始传输远程桌面画面"
        elif cat == "游戏":
            resp = "游戏服务器返回游戏状态和其他玩家数据"
        else:
            resp = "服务器返回响应数据给{}".format(app)
    else:
        resp = "本机处理后向{}回复确认".format(rip)

    return req, resp
