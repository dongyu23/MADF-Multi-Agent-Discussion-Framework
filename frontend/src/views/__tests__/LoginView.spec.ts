import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import LoginView from '../LoginView.vue'
import { createTestingPinia } from '@pinia/testing'
import Antd from 'ant-design-vue'

describe('LoginView', () => {
  it('renders login form', () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [
          createTestingPinia({ createSpy: vi.fn }),
          Antd
        ],
        stubs: {
            'router-link': true
        }
      }
    })
    expect(wrapper.text()).toContain('Login')
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })
})
