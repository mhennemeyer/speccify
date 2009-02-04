require File.dirname(__FILE__) + "/rails_test_helper.rb"

module MyModelsHelper
  def helper_method
    '<be value="helpful">'
  end
end

describe MyModelsHelper, :type => ActionView::TestCase do

  it "is helpful" do
    helper_method.should =~ /helpful/
  end
  
  describe "nested context" do
    it "is still helpful" do
      helper_method.should =~ /helpful/
    end
  end
  
end
