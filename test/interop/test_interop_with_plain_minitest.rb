require File.dirname(__FILE__) + "/../test_helper.rb"
require 'rubygems'
require "minitest/unit"

class TestInterop < MiniTest::Unit::TestCase
  def test_whatever
    assert(true)
  end
end

describe "An example group containing a testcase definition" do
  
  class TestInterop2 < MiniTest::Unit::TestCase
    def test_whatever
      assert(true)
    end
  end

end