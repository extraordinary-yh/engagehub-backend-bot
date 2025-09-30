#!/usr/bin/env python
"""
Live Discord Testing Script - Real-time notifications to your Discord server
Run this while your bot is running to see live test results
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime
import os

# CONFIGURATION - UPDATE THESE VALUES
DISCORD_WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"  # Replace with your Discord webhook URL
BACKEND_URL = "http://localhost:8000/api/bot/"  # Your Django backend URL
TEST_USER_ID = "YOUR_TEST_USER_DISCORD_ID_HERE"  # Replace with a real Discord user ID

async def send_discord_notification(message, embed_data=None):
    """Send notification to Discord channel via webhook"""
    if DISCORD_WEBHOOK_URL == "YOUR_WEBHOOK_URL_HERE":
        print("⚠️ Please configure DISCORD_WEBHOOK_URL in the script")
        return False
    
    payload = {"content": message}
    if embed_data:
        payload["embeds"] = [embed_data]
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload) as response:
                return response.status == 204
    except Exception as e:
        print(f"❌ Failed to send Discord notification: {e}")
        return False

async def create_test_embed(title, description, color=0x00ff00):
    """Create Discord embed"""
    return {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Live Test - EngageHub Bot"}
    }

async def test_command(command_name, description, points):
    """Test a single command and send results to Discord"""
    
    # Create embed for this test
    embed = await create_test_embed(
        f"🧪 Testing: !{command_name}",
        f"**Points:** {points}\n**Description:** {description[:200]}...\n**Status:** Testing...",
        0xffaa00
    )
    
    await send_discord_notification(f"🔄 **Starting test for `!{command_name}`**", embed)
    
    # Convert command name to backend action
    action_map = {
        "joblead": "submit-job-lead",
        "thoughtfulreply": "submit-thoughtful-reply", 
        "resumefeedback": "submit-resume-feedback",
        "studygroup": "submit-study-group",
        "walkthrough": "submit-resource-walkthrough",
        "mockinterview": "submit-mock-interview",
        "teachshare": "submit-teach-share",
        "peermentor": "submit-peer-mentor",
        "minievent": "submit-mini-event",
        "referral": "submit-professional-referral",
        "exclusive": "submit-exclusive-resource",
        "workshop": "submit-external-workshop"
    }
    
    action = action_map.get(command_name, f"submit-{command_name}")
    
    payload = {
        "action": action,
        "discord_id": TEST_USER_ID,
        "description": description
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                BACKEND_URL, 
                json=payload,
                headers={"Content-Type": "application/json", "X-Bot-Secret": "your-bot-secret"}
            ) as response:
                
                if response.status == 201:
                    result = await resp.json()
                    submission_id = result.get('submission_id', 'N/A')
                    
                    # Success embed
                    success_embed = await create_test_embed(
                        f"✅ Success: !{command_name}",
                        f"**Points:** {points}\n**Submission ID:** {submission_id}\n**Status:** ✅ Submitted successfully\n**Description:** {description[:150]}...",
                        0x00ff00
                    )
                    await send_discord_notification(f"✅ **`!{command_name}` test PASSED**", success_embed)
                    return True
                    
                else:
                    error_text = await response.text()
                    # Error embed
                    error_embed = await create_test_embed(
                        f"❌ Failed: !{command_name}",
                        f"**Points:** {points}\n**Status:** ❌ Failed\n**Error:** {error_text[:200]}\n**Description:** {description[:100]}...",
                        0xff0000
                    )
                    await send_discord_notification(f"❌ **`!{command_name}` test FAILED**", error_embed)
                    return False
                    
    except Exception as e:
        # Exception embed
        error_embed = await create_test_embed(
            f"💥 Error: !{command_name}",
            f"**Points:** {points}\n**Status:** 💥 Exception occurred\n**Error:** {str(e)[:200]}\n**Description:** {description[:100]}...",
            0xff0000
        )
        await send_discord_notification(f"💥 **`!{command_name}` test ERROR**", error_embed)
        return False

async def run_all_tests():
    """Run all command tests with live Discord notifications"""
    
    # Test commands with realistic descriptions
    test_commands = [
        ("joblead", "Found Google SWE Internship Summer 2025 posted in #internships channel. Application link shared, requires Python/Java skills, deadline October 15th.", 10),
        ("thoughtfulreply", "Helped Sarah with behavioral interview preparation for 45 minutes. Provided 8 STAR method examples, practiced 3 scenarios, gave feedback on communication.", 25),
        ("resumefeedback", "Reviewed Alex's software engineering resume for 1.5 hours. Fixed formatting inconsistencies, added quantified achievements, restructured technical skills section.", 75),
        ("studygroup", "Led 2-hour Python fundamentals study session for 8 beginner students. Covered variables, loops, functions, and debugging techniques. Created 15 practice exercises.", 100),
        ("walkthrough", "Created comprehensive AWS Cloud Practitioner certification study guide. 12-page PDF with exam topics, practice questions, cost breakdown, and resource links.", 100),
        ("mockinterview", "Hosted 45-minute technical interview simulation for Jennifer targeting software developer role. Covered algorithms, system design basics, behavioral questions.", 150),
        ("teachshare", "Taught 'Git Version Control for Beginners' workshop to 12 students. 2.5-hour session with live coding demonstrations, branching strategies, conflict resolution.", 200),
        ("peermentor", "Mentored David through career transition from marketing to software development over 4 weeks. Weekly 1-hour sessions covering resume, portfolio, interview prep.", 250),
        ("minievent", "Organized virtual networking session 'Tech Career Panel' with 28 attendees. Coordinated 3 industry speakers, created breakout rooms, facilitated introductions.", 300),
        ("referral", "Connected Maria with Microsoft senior software engineer for SWE internship opportunity. Provided introduction email, shared her resume, highlighted relevant projects.", 500),
        ("exclusive", "Shared invite-only Google Cloud certification scholarship program link with community. Limited to 50 spots, covers full cost of certification, includes study materials.", 750),
        ("workshop", "Attended 8-hour Google Cloud Professional Data Engineer certification workshop. Earned completion certificate, created summary notes, hosted community Q&A session.", 1000)
    ]
    
    # Send start notification
    start_embed = await create_test_embed(
        "🚀 **Live Testing Started**",
        f"**Total Commands:** {len(test_commands)}\n**Test User:** {TEST_USER_ID}\n**Backend:** {BACKEND_URL}\n**Time:** {datetime.now().strftime('%H:%M:%S')}",
        0x0099ff
    )
    await send_discord_notification("🚀 **Starting live command testing...**", start_embed)
    
    # Track results
    passed = 0
    failed = 0
    
    # Test each command
    for i, (command, description, points) in enumerate(test_commands, 1):
        print(f"Testing {i}/{len(test_commands)}: {command}")
        
        success = await test_command(command, description, points)
        if success:
            passed += 1
        else:
            failed += 1
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Send final results
    final_embed = await create_test_embed(
        "🏁 **Testing Complete**",
        f"**✅ Passed:** {passed}/{len(test_commands)}\n**❌ Failed:** {failed}/{len(test_commands)}\n**Success Rate:** {(passed/len(test_commands)*100):.1f}%\n**Time:** {datetime.now().strftime('%H:%M:%S')}",
        0x00ff00 if failed == 0 else 0xff9900 if failed < 3 else 0xff0000
    )
    await send_discord_notification("🏁 **All tests completed!**", final_embed)
    
    return passed, failed

async def main():
    """Main execution"""
    print("""
🧪 **Live Discord Command Testing**
================================

This script will test all 12 new commands and send live results to your Discord server.

**Setup Required:**
1. Create a Discord webhook in your admin channel
2. Update DISCORD_WEBHOOK_URL in this script
3. Update TEST_USER_ID with a real Discord user ID
4. Make sure your Django backend is running
5. Make sure your Discord bot is running

**Commands to test:**
- !joblead (10 pts)
- !thoughtfulreply (25 pts)
- !resumefeedback (75 pts)
- !studygroup (100 pts)
- !walkthrough (100 pts)
- !mockinterview (150 pts)
- !teachshare (200 pts)
- !peermentor (250 pts)
- !minievent (300 pts)
- !referral (500 pts)
- !exclusive (750 pts)
- !workshop (1000 pts)

""")
    
    if DISCORD_WEBHOOK_URL == "YOUR_WEBHOOK_URL_HERE":
        print("❌ Please configure DISCORD_WEBHOOK_URL first!")
        print("""
🔗 **How to create a Discord webhook:**
1. Right-click your admin channel in Discord
2. Select "Edit Channel"
3. Go to "Integrations" → "Webhooks"
4. Click "Create Webhook"
5. Copy the webhook URL
6. Paste it in this script
        """)
        return
    
    if TEST_USER_ID == "YOUR_TEST_USER_DISCORD_ID_HERE":
        print("❌ Please configure TEST_USER_ID with a real Discord user ID!")
        return
    
    print(f"🎯 Testing with user ID: {TEST_USER_ID}")
    print(f"📢 Sending results to Discord webhook")
    print(f"🔧 Backend URL: {BACKEND_URL}")
    print()
    
    # Run the tests
    passed, failed = await run_all_tests()
    
    print(f"\n🏁 **Final Results:**")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")

if __name__ == "__main__":
    asyncio.run(main())


