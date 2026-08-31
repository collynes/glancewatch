# Enabling Feedback Channels - Quick Setup

## ✅ What's Already Done

1. **Web UI Feedback Link** - Added to dashboard footer
2. **GitHub Discussions Template** - Structured feedback survey ready
3. **README Feedback Section** - Prominent call-to-action added
4. **Documentation** - Complete guide in `docs/USER_FEEDBACK_GUIDE.md`

## 🚀 Manual Steps Required (5 minutes)

### 1. Enable GitHub Discussions

Go to: https://github.com/collynes/glancewatch/settings

1. Scroll to **Features** section
2. Check ✅ **Discussions**
3. Click **Save changes**

### 2. Create Discussion Categories

Once enabled, go to: https://github.com/collynes/glancewatch/discussions

1. Click **⚙️ Settings** (top right)
2. Create these categories:

   **📣 General**
   - Description: "General discussions about GlanceWatch"
   - Format: Discussion

   **💬 Feedback**
   - Description: "Share your experience and suggestions"
   - Format: Discussion
   - Use template: `.github/DISCUSSION_TEMPLATE/feedback.yml`

   **💡 Ideas**
   - Description: "Feature requests and ideas"
   - Format: Discussion

   **🙋 Q&A**
   - Description: "Questions and answers"
   - Format: Q&A

   **📢 Show and Tell**
   - Description: "Show off your setup!"
   - Format: Discussion

### 3. Pin Welcome Post

Create a pinned discussion in **General**:

```markdown
# Welcome to GlanceWatch Discussions! 👋

Thanks for being here! This is the place to:

- 💬 **Share feedback** on your experience
- 💡 **Suggest features** you'd like to see
- 🙋 **Ask questions** about setup and usage
- 📢 **Show off** your monitoring setup
- 🤝 **Help others** in the community

## Quick Links

- 📚 [Documentation](https://github.com/collynes/glancewatch#readme)
- 🐛 [Report bugs](https://github.com/collynes/glancewatch/issues)
- 📦 [PyPI Package](https://pypi.org/project/glancewatch/)

Looking forward to hearing from you!
```

## 📊 Monitoring Feedback

Check these regularly:

1. **GitHub Discussions** - https://github.com/collynes/glancewatch/discussions
2. **GitHub Issues** - https://github.com/collynes/glancewatch/issues
3. **PyPI Download Stats** - Run `curl -s "https://pypistats.org/api/packages/glancewatch/recent" | python3 -m json.tool`
4. **npm Stats** - Check https://www.npmjs.com/package/glancewatch

## 🎯 First Week Goals

- [ ] Get 3+ feedback submissions
- [ ] Respond to all within 24 hours
- [ ] Identify 1-2 quick wins to implement
- [ ] Thank every contributor

## 📣 Optional: Promote Feedback Channels

**Post to communities:**
- Reddit: r/selfhosted, r/homelab
- Hacker News: "Show HN: GlanceWatch - Lightweight system monitoring"
- Dev.to: Write a "Building in Public" post

**Message:**
> "Just launched GlanceWatch feedback channels! If you're using it (or tried it), would love to hear your thoughts: [link]. Takes 2 min, and your input directly shapes what we build next. 🙏"

---

All set! Once Discussions are enabled, users can share feedback directly from your dashboard. 🎉
