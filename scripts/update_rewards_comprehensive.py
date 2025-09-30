#!/usr/bin/env python3
"""
Comprehensive script to update the entire rewards system with the new 4-tier structure.

This script will:
1. Clear all existing rewards  
2. Create all new rewards according to the provided comprehensive list
3. Set stock levels (99999 for "unlimited" items)
4. Assign proper tiers and categories
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Incentive

def clear_existing_rewards():
    """Clear all existing rewards"""
    print("🗑️ Clearing existing rewards...")
    count = Incentive.objects.count()
    Incentive.objects.all().delete()
    print(f"✅ Deleted {count} existing rewards")

def create_new_rewards():
    """Create all new rewards according to the comprehensive list"""
    print("🆕 Creating new comprehensive reward system...")
    
    # Define all rewards with their properties
    rewards = [
        # TIER 1 - Foundational Rewards
        {
            'name': 'EngageHub Badge or Leaderboard Recognition',
            'points_required': 25,
            'stock_available': 0,
            'tier': 'tier1',
            'category': 'digital',
            'description': 'A digital badge for your profile or a shout-out on the leaderboard to signal your status in the community.',
            'is_active': False  # 0 stock = inactive
        },
        {
            'name': 'Digital Badges ("Case Prep Pro," etc.)',
            'points_required': 25,
            'stock_available': 0,
            'tier': 'tier1',
            'category': 'digital',
            'description': 'Earn a digital, shareable badge for your LinkedIn or email signature to certify your prep milestones.',
            'is_active': False  # 0 stock = inactive
        },
        {
            'name': 'ATS Optimization Guide',
            'points_required': 35,
            'stock_available': 99999,  # Unlimited
            'tier': 'tier1',
            'category': 'digital',
            'description': 'A comprehensive guide on how to format your resume to get past automated screeners and into human hands.',
            'is_active': True
        },
        {
            'name': 'E-books / Guides',
            'points_required': 35,
            'stock_available': 99999,  # Unlimited
            'tier': 'tier1',
            'category': 'digital',
            'description': 'Instantly download a guide like "Top 50 Consulting Interview Questions" or "Finance Excel Shortcuts."',
            'is_active': True
        },
        {
            'name': 'LinkedIn Headline & About Me Template Pack',
            'points_required': 40,
            'stock_available': 99999,  # Unlimited
            'tier': 'tier1',
            'category': 'digital',
            'description': 'Optimize your LinkedIn profile with pre-built examples tailored to land roles in tech, finance, and consulting.',
            'is_active': True
        },
        {
            'name': 'Finance & Consulting Cheat Sheets',
            'points_required': 40,
            'stock_available': 99999,  # Unlimited
            'tier': 'tier1',
            'category': 'digital',
            'description': 'Quick-reference guides covering key concepts like DCF, valuation, and strategy frameworks.',
            'is_active': True
        },
        {
            'name': 'Resume Template Bundle',
            'points_required': 50,
            'stock_available': 99999,  # Unlimited (as requested)
            'tier': 'tier1',
            'category': 'digital',
            'description': 'A pack of consulting, finance, and tech-ready resume templates to make your application stand out.',
            'is_active': True
        },
        {
            'name': 'Azure E-Learning',
            'points_required': 50,
            'stock_available': 998,  # Keep existing stock
            'tier': 'tier1',
            'category': 'digital',
            'description': 'A curated playlist of the best free labs, GitHub repos, and tutorials to prepare for cloud certifications.',
            'is_active': True,
            'sponsor': 'Microsoft'
        },
        {
            'name': 'Cover Letter & Email Outreach Templates',
            'points_required': 50,
            'stock_available': 99999,  # Unlimited
            'tier': 'tier1',
            'category': 'digital',
            'description': 'A collection of proven templates for cold emails, networking requests, and formal cover letters.',
            'is_active': True
        },
        {
            'name': 'Professional Headshot Editing / LinkedIn Banner Templates',
            'points_required': 50,
            'stock_available': 99999,  # Unlimited
            'tier': 'tier1',
            'category': 'digital',
            'description': 'Use AI tools and premium templates to create a professional LinkedIn banner and polish your headshot.',
            'is_active': True
        },
        {
            'name': 'Networking Event Invites',
            'points_required': 75,
            'stock_available': 100,
            'tier': 'tier1',
            'category': 'experiences',
            'description': 'Receive an invitation to an exclusive virtual meetup with peers and professionals in your target industry.',
            'is_active': True
        },

        # TIER 2 - Premium Resources & Scaled Access
        {
            'name': 'Azure Exam Vouchers',
            'points_required': 100,
            'stock_available': 50,  # Keep existing stock
            'tier': 'tier2',
            'category': 'digital',
            'description': 'Receive a free exam voucher code to sit for your official Microsoft Azure certification exam.',
            'is_active': True,
            'sponsor': 'Microsoft'
        },
        {
            'name': 'Peer Accountability Groups',
            'points_required': 100,
            'stock_available': 50,
            'tier': 'tier2',
            'category': 'services',
            'description': 'Get placed into a curated "prep pod" with motivated peers who are targeting the same roles as you.',
            'is_active': True
        },
        {
            'name': 'Free or Discounted Coursera / edX / Udemy Courses',
            'points_required': 100,  # Lower end of the 100-250 range
            'stock_available': 0,
            'tier': 'tier2',
            'category': 'digital',
            'description': 'Get a voucher for a free or heavily discounted online course to earn a new certificate or skill.',
            'is_active': False
        },
        {
            'name': 'Case Interview Prep Pack',
            'points_required': 125,
            'stock_available': 99999,  # Unlimited
            'tier': 'tier2',
            'category': 'digital',
            'description': 'A complete digital toolkit with practice cases, frameworks, and example solutions for consulting interviews.',
            'is_active': True
        },
        {
            'name': 'Technical Prep Packs',
            'points_required': 125,
            'stock_available': 99999,  # Unlimited
            'tier': 'tier2',
            'category': 'digital',
            'description': 'Sharpen your technical skills with prep materials for SQL, Python, Excel, and financial modeling.',
            'is_active': True
        },
        {
            'name': 'Coffee Chats with Professionals (Group-based)',
            'points_required': 150,
            'stock_available': 75,
            'tier': 'tier2',
            'category': 'services',
            'description': 'An informal, small-group networking chat with an industry professional to ask questions and build connections.',
            'is_active': True
        },
        {
            'name': 'Spotlight Feature on EngageHub Channels',
            'points_required': 150,
            'stock_available': 25,
            'tier': 'tier2',
            'category': 'other',
            'description': 'Be featured as a top performer on EngageHub\'s official channels for recognition and visibility.',
            'is_active': True
        },
        {
            'name': '"Ask Me Anything" with Alumni',
            'points_required': 175,
            'stock_available': 100,
            'tier': 'tier2',
            'category': 'services',
            'description': 'Join an exclusive group Q&A session with recently placed alumni to learn about their recruiting journey.',
            'is_active': True
        },

        # TIER 3 - High-Value Human Interaction
        {
            'name': 'Resume Review',
            'points_required': 250,  # Updated as requested
            'stock_available': 50,
            'tier': 'tier3',
            'category': 'services',
            'description': 'Get your resume personally reviewed by an industry expert who will provide actionable, written feedback.',
            'is_active': True
        },
        {
            'name': 'Exclusive Masterclasses / Workshops',
            'points_required': 250,
            'stock_available': 100,
            'tier': 'tier3',
            'category': 'services',
            'description': 'Gain access to a live or recorded expert-led workshop on topics like "Breaking into MBB" or "IB Analyst Life."',
            'is_active': True
        },
        {
            'name': 'Recruiter List Access',
            'points_required': 300,
            'stock_available': 200,
            'tier': 'tier3',
            'category': 'services',
            'description': 'Unlock a curated, private list of recruiter contacts at top firms to accelerate your job outreach.',
            'is_active': True
        },
        {
            'name': 'Mock Interviews',
            'points_required': 400,
            'stock_available': 30,
            'tier': 'tier3',
            'category': 'services',
            'description': 'Practice a full case, behavioral, or technical interview with a trained student leader or alumnus and get direct feedback.',
            'is_active': True
        },
        {
            'name': 'Priority Access to EngageHub Fellowship Applications',
            'points_required': 450,
            'stock_available': 50,
            'tier': 'tier3',
            'category': 'services',
            'description': 'Get your fellowship application reviewed early or secure a guaranteed first-round interview slot.',
            'is_active': True
        },

        # TIER 4 - Elite & Bespoke Rewards
        {
            'name': '1-on-1 Career Coaching Session',
            'points_required': 500,
            'stock_available': 50,  # Keep existing stock
            'tier': 'tier4',
            'category': 'services',
            'description': 'A personalized 30-minute session with a volunteer industry champion to get tailored career advice.',
            'is_active': True
        },
        {
            'name': 'Direct Referrals Into EngageHub Network',
            'points_required': 750,
            'stock_available': 10,
            'tier': 'tier4',
            'category': 'services',
            'description': 'Receive a direct, warm introduction or referral from EngageHub to a key contact for a role or special project.',
            'is_active': True
        }
    ]

    created_count = 0
    for reward_data in rewards:
        try:
            reward = Incentive.objects.create(**reward_data)
            print(f"✅ Created: {reward.name} ({reward.points_required} pts, Tier: {reward.get_tier_display()})")
            created_count += 1
        except Exception as e:
            print(f"❌ Failed to create {reward_data['name']}: {e}")

    print(f"\n🎉 Successfully created {created_count}/{len(rewards)} rewards!")

def show_final_summary():
    """Show the final rewards summary"""
    print("\n" + "="*80)
    print("🎁 COMPREHENSIVE REWARDS SYSTEM - FINAL SUMMARY")
    print("="*80)
    
    # Group by tier
    for tier_key, tier_name in [('tier1', 'Tier 1 (Foundational Rewards)'), 
                                ('tier2', 'Tier 2 (Premium Resources & Scaled Access)'),
                                ('tier3', 'Tier 3 (High-Value Human Interaction)'),
                                ('tier4', 'Tier 4 (Elite & Bespoke Rewards)')]:
        
        tier_rewards = Incentive.objects.filter(tier=tier_key).order_by('points_required')
        if tier_rewards:
            print(f"\n🏆 {tier_name.upper()}")
            print("-" * len(tier_name))
            
            for reward in tier_rewards:
                status = "✅ ACTIVE" if reward.is_active and reward.stock_available > 0 else "❌ INACTIVE"
                stock_display = "Unlimited" if reward.stock_available == 99999 else str(reward.stock_available)
                print(f"  • {reward.name} ({reward.points_required} pts)")
                print(f"    Stock: {stock_display} | {status}")
                print()

    # Summary stats
    total_rewards = Incentive.objects.count()
    active_rewards = Incentive.objects.filter(is_active=True, stock_available__gt=0).count()
    unlimited_rewards = Incentive.objects.filter(stock_available=99999).count()
    
    print(f"📊 FINAL STATISTICS:")
    print(f"  • Total rewards: {total_rewards}")
    print(f"  • Active & available: {active_rewards}")
    print(f"  • Unlimited stock items: {unlimited_rewards}")
    print(f"  • Resume Review updated to: 250 points ✅")
    print(f"  • Resume Template Bundle: Unlimited stock ✅")

def main():
    """Main execution function"""
    print("🚀 Starting comprehensive rewards system update...")
    print("This will completely replace the current reward system.\n")
    
    clear_existing_rewards()
    print()
    create_new_rewards()
    print()
    show_final_summary()
    
    print("\n✨ Comprehensive rewards system update completed!")

if __name__ == "__main__":
    main()
